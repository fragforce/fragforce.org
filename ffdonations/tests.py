import importlib
from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from requests.exceptions import HTTPError

from .admin import ParticipantModelAdmin, TeamModelAdmin
from .helpers import el_request_sleeper
from .models import DonationModel, EventModel, ParticipantModel, TeamModel
from .tasks.donations import (
    update_donations_if_needed_participant,
    update_donations_if_needed_team,
    update_donations_participant,
    update_donations_team,
)
from .tasks.participants import update_participants, update_participants_if_needed
from .tasks.teams import update_teams, update_teams_if_needed

# tasks/__init__.py does `from .tiltify import *` which overwrites the `teams`
# and `donations` attributes on the package with the tiltify submodules. Use
# importlib to get the correct EL task modules directly from sys.modules.
_teams_tasks = importlib.import_module('ffdonations.tasks.teams')
_participants_tasks = importlib.import_module('ffdonations.tasks.participants')
_donations_tasks = importlib.import_module('ffdonations.tasks.donations')


def _http_error(status_code):
    response = MagicMock()
    response.status_code = status_code
    return HTTPError(response=response)


def _make_request(factory):
    request = factory.get('/')
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


class TeamAdminSyncDonationsTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = TeamModelAdmin(TeamModel, self.site)
        self.factory = RequestFactory()

    def test_queues_task_for_each_selected_team(self):
        TeamModel.objects.create(id=1001)
        TeamModel.objects.create(id=1002)
        queryset = TeamModel.objects.filter(id__in=[1001, 1002])

        with patch('ffdonations.admin.update_donations_if_needed_team') as mock_task:
            self.admin.sync_donations(_make_request(self.factory), queryset)

        mock_task.delay.assert_has_calls([
            call(teamID=1001),
            call(teamID=1002),
        ], any_order=True)
        self.assertEqual(mock_task.delay.call_count, 2)

    def test_queues_no_tasks_for_empty_queryset(self):
        queryset = TeamModel.objects.none()

        with patch('ffdonations.admin.update_donations_if_needed_team') as mock_task:
            self.admin.sync_donations(_make_request(self.factory), queryset)

        mock_task.delay.assert_not_called()


class ParticipantAdminSyncDonationsTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = ParticipantModelAdmin(ParticipantModel, self.site)
        self.factory = RequestFactory()

    def test_queues_task_for_each_selected_participant(self):
        ParticipantModel.objects.create(id=2001)
        ParticipantModel.objects.create(id=2002)
        queryset = ParticipantModel.objects.filter(id__in=[2001, 2002])

        with patch('ffdonations.admin.update_donations_if_needed_participant') as mock_task:
            self.admin.sync_donations(_make_request(self.factory), queryset)

        mock_task.delay.assert_has_calls([
            call(participantID=2001),
            call(participantID=2002),
        ], any_order=True)
        self.assertEqual(mock_task.delay.call_count, 2)

    def test_queues_no_tasks_for_empty_queryset(self):
        queryset = ParticipantModel.objects.none()

        with patch('ffdonations.admin.update_donations_if_needed_participant') as mock_task:
            self.admin.sync_donations(_make_request(self.factory), queryset)

        mock_task.delay.assert_not_called()


class ElRequestSleeperTest(TestCase):
    def _parsed(self, url='https://www.extra-life.org/api/teams/12345'):
        return urlparse(url)

    def test_sleeps_for_longest_timer_and_resets_all_keys(self):
        url = 'https://www.extra-life.org/api/teams/12345'
        parsed = self._parsed(url)

        with patch('ffdonations.helpers.r_timers') as mock_timers, \
                patch('ffdonations.helpers.time') as mock_time:
            mock_timers.make_key.side_effect = lambda *a, **kw: '_'.join(
                [a[0]] + [f"{k}={v}" for k, v in sorted(kw.items())]
            )
            mock_timers.time_until.side_effect = [
                timedelta(seconds=0),   # global
                timedelta(seconds=0),   # host
                timedelta(seconds=5),   # url
            ]

            result = el_request_sleeper(url=url, data=None, parsed=parsed)

        mock_time.sleep.assert_called_once_with(5)
        self.assertEqual(result, 'url_sleep')
        self.assertEqual(mock_timers.reset.call_count, 3)

    def test_no_sleep_when_all_timers_zero(self):
        url = 'https://www.extra-life.org/api/teams/12345'
        parsed = self._parsed(url)

        with patch('ffdonations.helpers.r_timers') as mock_timers, \
                patch('ffdonations.helpers.time') as mock_time:
            mock_timers.make_key.side_effect = lambda *a, **kw: '_'.join(
                [a[0]] + [f"{k}={v}" for k, v in sorted(kw.items())]
            )
            mock_timers.time_until.return_value = timedelta(seconds=0)

            el_request_sleeper(url=url, data=None, parsed=parsed)

        mock_time.sleep.assert_called_once_with(0)
        self.assertEqual(mock_timers.reset.call_count, 3)


class UpdateTeams404Test(TestCase):
    def test_404_untracks_existing_team(self):
        team = TeamModel.objects.create(id=5001, tracked=True)
        mock_api = MagicMock()
        mock_api.team.side_effect = _http_error(404)

        with patch.object(_teams_tasks, '_make_team', return_value=mock_api):
            update_teams.apply(kwargs={'teams': [5001]})

        team.refresh_from_db()
        self.assertFalse(team.tracked)

    def test_404_on_unknown_team_silently_passes(self):
        mock_api = MagicMock()
        mock_api.team.side_effect = _http_error(404)

        with patch.object(_teams_tasks, '_make_team', return_value=mock_api):
            update_teams.apply(kwargs={'teams': [9999]})

    def test_non_404_error_reraises(self):
        mock_api = MagicMock()
        mock_api.team.side_effect = _http_error(500)

        with patch.object(_teams_tasks, '_make_team', return_value=mock_api):
            with self.assertRaises(HTTPError):
                update_teams.apply(kwargs={'teams': [5001]}, throw=True)

    def test_404_on_one_team_does_not_block_others(self):
        team_ok = TeamModel.objects.create(id=5002, tracked=True)
        mock_team = MagicMock()
        mock_team.teamID = 5002
        mock_team.eventID = None
        mock_team.name = 'Team OK'
        mock_team.createdDateUTC = None
        mock_team.fundraisingGoal = 0
        mock_team.numDonations = 0
        mock_team.sumDonations = 0
        mock_team.raw = {}
        mock_api = MagicMock()
        mock_api.team.side_effect = [_http_error(404), mock_team]

        with patch.object(_teams_tasks, '_make_team', return_value=mock_api), \
                patch.object(_donations_tasks, 'update_donations_if_needed_team'):
            result = update_teams.apply(kwargs={'teams': [5001, 5002]}, throw=True).result

        team_ok.refresh_from_db()
        self.assertIn(team_ok.guid, result)


class UpdateParticipants404Test(TestCase):
    def test_404_on_participants_for_team_untracks_team(self):
        team = TeamModel.objects.create(id=settings.EXTRALIFE_TEAMID, tracked=True)
        mock_api = MagicMock()
        mock_api.participants_for_team.side_effect = _http_error(404)

        with patch.object(_participants_tasks, '_make_p', return_value=mock_api):
            result = update_participants.apply(throw=True).result

        team.refresh_from_db()
        self.assertFalse(team.tracked)
        self.assertEqual(result, [])

    def test_non_404_on_participants_for_team_reraises(self):
        mock_api = MagicMock()
        mock_api.participants_for_team.side_effect = _http_error(500)

        with patch.object(_participants_tasks, '_make_p', return_value=mock_api):
            with self.assertRaises(HTTPError):
                update_participants.apply(throw=True)

    def test_404_on_individual_participant_untracks_it(self):
        participant = ParticipantModel.objects.create(id=3001, tracked=True)
        mock_api = MagicMock()
        mock_api.participant.side_effect = _http_error(404)

        with patch.object(_participants_tasks, '_make_p', return_value=mock_api):
            update_participants.apply(kwargs={'participants': [3001]}, throw=True)

        participant.refresh_from_db()
        self.assertFalse(participant.tracked)

    def test_non_404_on_individual_participant_reraises(self):
        mock_api = MagicMock()
        mock_api.participant.side_effect = _http_error(500)

        with patch.object(_participants_tasks, '_make_p', return_value=mock_api):
            with self.assertRaises(HTTPError):
                update_participants.apply(kwargs={'participants': [3001]}, throw=True)


class UpdateDonationsTeam404Test(TestCase):
    def setUp(self):
        self.event = EventModel.objects.create(id=2026, tracked=True)
        self.team = TeamModel.objects.create(id=6001, tracked=True, event=self.event)

    def test_404_untracks_team_and_returns_empty_list(self):
        mock_api = MagicMock()
        mock_api.donations_for_team.side_effect = _http_error(404)

        with patch.object(_donations_tasks, '_make_d', return_value=mock_api), \
                patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]):
            result = update_donations_team.apply(
                kwargs={'teamID': self.team.id}, throw=True
            ).result

        self.team.refresh_from_db()
        self.assertFalse(self.team.tracked)
        self.assertEqual(result, [])

    def test_non_404_error_reraises(self):
        mock_api = MagicMock()
        mock_api.donations_for_team.side_effect = _http_error(500)

        with patch.object(_donations_tasks, '_make_d', return_value=mock_api), \
                patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]):
            with self.assertRaises(HTTPError):
                update_donations_team.apply(
                    kwargs={'teamID': self.team.id}, throw=True
                )


class UpdateDonationsParticipant404Test(TestCase):
    def setUp(self):
        self.event = EventModel.objects.create(id=2026, tracked=True)
        self.participant = ParticipantModel.objects.create(
            id=4001, tracked=True, event=self.event
        )

    def test_404_untracks_participant_and_returns_none(self):
        mock_api = MagicMock()
        mock_api.donations_for_participants.side_effect = _http_error(404)

        with patch.object(_donations_tasks, '_make_d', return_value=mock_api), \
                patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]):
            result = update_donations_participant.apply(
                kwargs={'participant_id': self.participant.id}, throw=True
            ).result

        self.participant.refresh_from_db()
        self.assertFalse(self.participant.tracked)
        self.assertIsNone(result)

    def test_non_404_error_reraises(self):
        mock_api = MagicMock()
        mock_api.donations_for_participants.side_effect = _http_error(500)

        with patch.object(_donations_tasks, '_make_d', return_value=mock_api), \
                patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]):
            with self.assertRaises(HTTPError):
                update_donations_participant.apply(
                    kwargs={'participant_id': self.participant.id}, throw=True
                )


# ---------------------------------------------------------------------------
# Frequency gating helpers
# ---------------------------------------------------------------------------

# Short frequency windows used by all gating tests so we don't need real delays
_FREQ_MIN = timedelta(minutes=5)
_FREQ_MAX = timedelta(minutes=15)


def _make_event(event_id=2026, tracked=True):
    return EventModel.objects.create(id=event_id, tracked=tracked)


def _stamp_recent(qs):
    """ Set last_updated to 1 minute ago - within the MIN window, so updates should be skipped. """
    qs.update(last_updated=timezone.now() - timedelta(minutes=1))


def _stamp_stale(qs):
    """ Set last_updated to 1 hour ago - beyond the MAX window, so updates should be forced. """
    qs.update(last_updated=timezone.now() - timedelta(hours=1))


# ---------------------------------------------------------------------------
# update_teams_if_needed gating tests
# ---------------------------------------------------------------------------

@override_settings(EL_TEAM_UPDATE_FREQUENCY_MIN=_FREQ_MIN, EL_TEAM_UPDATE_FREQUENCY_MAX=_FREQ_MAX)
class UpdateTeamsIfNeededTest(TestCase):
    def setUp(self):
        self.event = _make_event()

    def test_calls_update_when_no_teams_exist(self):
        with patch.object(_teams_tasks, 'update_teams') as mock_update:
            update_teams_if_needed.apply(throw=True)
        mock_update.assert_called_once()

    def test_skips_update_when_tracked_team_recently_updated(self):
        team = TeamModel.objects.create(id=7001, tracked=True, event=self.event)
        _stamp_recent(TeamModel.objects.filter(id=team.id))

        with patch.object(_teams_tasks, 'update_teams') as mock_update:
            result = update_teams_if_needed.apply(throw=True).result

        mock_update.assert_not_called()
        self.assertIsNone(result)

    def test_forces_update_when_tracked_team_is_stale(self):
        team = TeamModel.objects.create(id=7002, tracked=True, event=self.event)
        _stamp_stale(TeamModel.objects.filter(id=team.id))

        with patch.object(_teams_tasks, 'update_teams') as mock_update:
            update_teams_if_needed.apply(throw=True)

        mock_update.assert_called_once()

    def test_calls_update_when_no_tracked_teams_exist(self):
        # Untracked teams exist but none are tracked - falls through to update
        TeamModel.objects.create(id=7003, tracked=False, event=self.event)

        with patch.object(_teams_tasks, 'update_teams') as mock_update:
            update_teams_if_needed.apply(throw=True)

        mock_update.assert_called_once()


# ---------------------------------------------------------------------------
# update_participants_if_needed gating tests
# ---------------------------------------------------------------------------

@override_settings(EL_PTCP_UPDATE_FREQUENCY_MIN=_FREQ_MIN, EL_PTCP_UPDATE_FREQUENCY_MAX=_FREQ_MAX)
class UpdateParticipantsIfNeededTest(TestCase):
    def setUp(self):
        self.event = _make_event()

    def test_calls_update_when_no_participants_exist(self):
        with patch.object(_participants_tasks, 'update_participants') as mock_update:
            update_participants_if_needed.apply(throw=True)
        mock_update.assert_called_once()

    def test_forces_update_when_tracked_participant_is_stale(self):
        p = ParticipantModel.objects.create(id=8001, tracked=True, event=self.event)
        _stamp_stale(ParticipantModel.objects.filter(id=p.id))

        with patch.object(_participants_tasks, 'update_participants') as mock_update:
            update_participants_if_needed.apply(throw=True)

        mock_update.assert_called_once()

    def test_skips_update_when_tracked_participant_recently_updated(self):
        p = ParticipantModel.objects.create(id=8002, tracked=True, event=self.event)
        _stamp_recent(ParticipantModel.objects.filter(id=p.id))

        with patch.object(_participants_tasks, 'update_participants') as mock_update:
            result = update_participants_if_needed.apply(throw=True).result

        mock_update.assert_not_called()
        self.assertIsNone(result)

    def test_calls_update_when_no_tracked_participants_exist(self):
        ParticipantModel.objects.create(id=8003, tracked=False, event=self.event)

        with patch.object(_participants_tasks, 'update_participants') as mock_update:
            update_participants_if_needed.apply(throw=True)

        mock_update.assert_called_once()


# ---------------------------------------------------------------------------
# update_donations_if_needed_team gating tests
# ---------------------------------------------------------------------------

@override_settings(
    EL_DON_TEAM_UPDATE_FREQUENCY_MIN=_FREQ_MIN,
    EL_DON_TEAM_UPDATE_FREQUENCY_MAX=_FREQ_MAX,
    MIN_EL_TEAMID=1000,
)
class UpdateDonationsIfNeededTeamTest(TestCase):
    def setUp(self):
        self.event = _make_event()
        self.team = TeamModel.objects.create(id=9001, tracked=True, event=self.event, numDonations=0)

    def _run(self, team_id=None):
        tid = team_id if team_id is not None else self.team.id
        with patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]), \
                patch.object(_donations_tasks, 'update_donations_team') as mock_update:
            result = update_donations_if_needed_team.apply(kwargs={'teamID': tid}, throw=True).result
        return result, mock_update

    def test_returns_none_when_team_does_not_exist(self):
        result, mock_update = self._run(team_id=99999)
        self.assertIsNone(result)
        mock_update.assert_not_called()

    def test_returns_none_when_team_not_in_current_events(self):
        other_event = EventModel.objects.create(id=3000, tracked=True)
        team = TeamModel.objects.create(id=9010, tracked=True, event=other_event, numDonations=0)

        with patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]), \
                patch.object(_donations_tasks, 'update_donations_team') as mock_update:
            result = update_donations_if_needed_team.apply(kwargs={'teamID': team.id}, throw=True).result

        self.assertIsNone(result)
        mock_update.assert_not_called()

    def test_untracks_and_returns_none_when_team_id_below_minimum(self):
        # teamID below MIN_EL_TEAMID means it's from a prior year - should be untracked silently
        old_team = TeamModel.objects.create(id=500, tracked=True, event=self.event)

        with patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]):
            update_donations_if_needed_team.apply(kwargs={'teamID': old_team.id}, throw=True)

        old_team.refresh_from_db()
        self.assertFalse(old_team.tracked)

    def test_forces_update_when_no_donations_in_db(self):
        _, mock_update = self._run()
        mock_update.assert_called_once_with(teamID=self.team.id)

    def test_skips_update_when_donations_recently_updated(self):
        DonationModel.objects.create(id='RECENT01', team=self.team, amount=10)
        _stamp_recent(DonationModel.objects.filter(id='RECENT01'))

        result, mock_update = self._run()

        mock_update.assert_not_called()
        self.assertIsNone(result)

    def test_returns_none_when_num_donations_is_none(self):
        # numDonations=None means we haven't synced team data yet - don't thrash
        self.team.numDonations = None
        self.team.save()
        DonationModel.objects.create(id='STALE01', team=self.team, amount=10)
        _stamp_stale(DonationModel.objects.filter(id='STALE01'))

        result, mock_update = self._run()

        mock_update.assert_not_called()
        self.assertIsNone(result)

    def test_forces_update_when_db_has_fewer_donations_than_expected(self):
        # numDonations=5 but only 1 in DB - known gap, force update
        self.team.numDonations = 5
        self.team.save()
        DonationModel.objects.create(id='GAP01', team=self.team, amount=10)
        _stamp_stale(DonationModel.objects.filter(id='GAP01'))

        _, mock_update = self._run()

        mock_update.assert_called_once_with(teamID=self.team.id)

    def test_forces_update_when_donations_are_stale(self):
        self.team.numDonations = 1
        self.team.save()
        DonationModel.objects.create(id='STALE02', team=self.team, amount=10)
        _stamp_stale(DonationModel.objects.filter(id='STALE02'))

        _, mock_update = self._run()

        mock_update.assert_called_once_with(teamID=self.team.id)


# ---------------------------------------------------------------------------
# update_donations_if_needed_participant gating tests
# ---------------------------------------------------------------------------

@override_settings(
    EL_DON_PTCP_UPDATE_FREQUENCY_MIN=_FREQ_MIN,
    EL_DON_PTCP_UPDATE_FREQUENCY_MAX=_FREQ_MAX,
    MIN_EL_PARTICIPANTID=1000,
)
class UpdateDonationsIfNeededParticipantTest(TestCase):
    def setUp(self):
        self.event = _make_event()
        self.participant = ParticipantModel.objects.create(
            id=10001, tracked=True, event=self.event, numDonations=0
        )

    def _run(self, participant_id=None):
        pid = participant_id if participant_id is not None else self.participant.id
        with patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]), \
                patch.object(_donations_tasks, 'update_donations_participant') as mock_update:
            result = update_donations_if_needed_participant.apply(
                kwargs={'participantID': pid}, throw=True
            ).result
        return result, mock_update

    def test_returns_none_when_participant_does_not_exist(self):
        result, mock_update = self._run(participant_id=99999)
        self.assertIsNone(result)
        mock_update.assert_not_called()

    def test_untracks_and_returns_none_when_participant_id_below_minimum(self):
        old_p = ParticipantModel.objects.create(id=500, tracked=True, event=self.event)

        with patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]):
            update_donations_if_needed_participant.apply(
                kwargs={'participantID': old_p.id}, throw=True
            )

        old_p.refresh_from_db()
        self.assertFalse(old_p.tracked)

    def test_returns_none_when_participant_not_tracked(self):
        self.participant.tracked = False
        self.participant.save()

        result, mock_update = self._run()

        mock_update.assert_not_called()
        self.assertIsNone(result)

    def test_returns_none_when_participant_not_in_current_events(self):
        other_event = EventModel.objects.create(id=4000, tracked=True)
        p = ParticipantModel.objects.create(id=10010, tracked=True, event=other_event)

        with patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]), \
                patch.object(_donations_tasks, 'update_donations_participant') as mock_update:
            result = update_donations_if_needed_participant.apply(
                kwargs={'participantID': p.id}, throw=True
            ).result

        mock_update.assert_not_called()
        self.assertIsNone(result)

    def test_forces_update_when_no_donations_in_db(self):
        _, mock_update = self._run()
        mock_update.assert_called_once_with(participant_id=self.participant.id)

    def test_skips_update_when_donations_recently_updated(self):
        DonationModel.objects.create(id='PRECENT02', participant=self.participant, amount=5)
        _stamp_recent(DonationModel.objects.filter(id='PRECENT02'))

        result, mock_update = self._run()

        mock_update.assert_not_called()
        self.assertIsNone(result)

    def test_forces_update_when_db_has_fewer_donations_than_expected(self):
        self.participant.numDonations = 5
        self.participant.save()
        DonationModel.objects.create(id='PGAP01', participant=self.participant, amount=5)
        _stamp_stale(DonationModel.objects.filter(id='PGAP01'))

        _, mock_update = self._run()

        mock_update.assert_called_once_with(participant_id=self.participant.id)

    def test_forces_update_when_donations_are_stale(self):
        self.participant.numDonations = 1
        self.participant.save()
        DonationModel.objects.create(id='PSTALE01', participant=self.participant, amount=5)
        _stamp_stale(DonationModel.objects.filter(id='PSTALE01'))

        _, mock_update = self._run()

        mock_update.assert_called_once_with(participant_id=self.participant.id)


# ---------------------------------------------------------------------------
# update_donations_team happy-path tests
# ---------------------------------------------------------------------------

from extralifeapi.donors import Donation as _Donation


def _make_donation(donation_id='DON001', amount=10.0, participant_id=None, team_id=None,
                   display_name='Donor Name', message='Great!'):
    """ Build a Donation namedtuple matching the extralifeapi structure. """
    return _Donation(
        donationID=donation_id,
        amount=amount,
        displayName=display_name,
        donorID='DONOR01',
        participantID=participant_id,
        teamID=team_id,
        message=message,
        createdDateUTC='2026-01-01T00:00:00.000+0000',
        avatarImageURL='https://example.com/avatar.gif',
        raw={'donationID': donation_id, 'amount': amount},
    )


class UpdateDonationsTeamHappyPathTest(TestCase):
    def setUp(self):
        self.event = EventModel.objects.create(id=2026, tracked=True)
        self.team = TeamModel.objects.create(id=11001, tracked=True, event=self.event)

    def _run(self, donations, team_id=None):
        tid = team_id if team_id is not None else self.team.id
        mock_api = MagicMock()
        mock_api.donations_for_team.return_value = donations
        with patch.object(_donations_tasks, '_make_d', return_value=mock_api), \
                patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]), \
                patch.object(_donations_tasks, 'note_new_donation') as mock_note:
            update_donations_team.apply(kwargs={'teamID': tid}, throw=True)
        return mock_note

    def test_donation_is_saved_to_db_with_correct_fields(self):
        donation = _make_donation(donation_id='DON001', amount=25.0, display_name='Alice', message='Go team!')
        self._run([donation])

        saved = DonationModel.objects.get(id='DON001')
        self.assertEqual(saved.amount, 25.0)
        self.assertEqual(saved.displayName, 'Alice')
        self.assertEqual(saved.message, 'Go team!')
        self.assertEqual(saved.team, self.team)

    def test_note_new_donation_called_per_donation(self):
        donations = [_make_donation('D1'), _make_donation('D2')]
        mock_note = self._run(donations)

        self.assertEqual(mock_note.apply_async.call_count, 2)

    def test_null_display_name_saved_as_empty_string(self):
        donation = _make_donation('DON002', display_name=None)
        self._run([donation])

        self.assertEqual(DonationModel.objects.get(id='DON002').displayName, '')

    def test_null_message_saved_as_empty_string(self):
        donation = _make_donation('DON003', message=None)
        self._run([donation])

        self.assertEqual(DonationModel.objects.get(id='DON003').message, '')

    def test_unknown_participant_stub_is_auto_created(self):
        # Donation references a participant not in DB - a tracked=False stub should be created
        donation = _make_donation('DON004', participant_id=55555)
        self._run([donation])

        participant = ParticipantModel.objects.get(id=55555)
        self.assertFalse(participant.tracked)

    def test_known_participant_is_linked_without_creating_stub(self):
        existing = ParticipantModel.objects.create(id=55556, tracked=True, event=self.event)
        donation = _make_donation('DON005', participant_id=55556)
        self._run([donation])

        self.assertEqual(ParticipantModel.objects.filter(id=55556).count(), 1)
        self.assertEqual(DonationModel.objects.get(id='DON005').participant, existing)

    def test_existing_donation_is_updated_not_duplicated(self):
        DonationModel.objects.create(id='DON006', team=self.team, amount=5.0)
        donation = _make_donation('DON006', amount=99.0)
        self._run([donation])

        self.assertEqual(DonationModel.objects.filter(id='DON006').count(), 1)
        self.assertEqual(DonationModel.objects.get(id='DON006').amount, 99.0)

    def test_returns_empty_list_when_team_id_is_none(self):
        mock_api = MagicMock()
        with patch.object(_donations_tasks, '_make_d', return_value=mock_api):
            result = update_donations_team.apply(kwargs={'teamID': None}, throw=True).result
        self.assertEqual(result, [])
        mock_api.donations_for_team.assert_not_called()

    def test_returns_none_when_team_not_tracked(self):
        self.team.tracked = False
        self.team.save()
        mock_api = MagicMock()
        with patch.object(_donations_tasks, '_make_d', return_value=mock_api), \
                patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]):
            result = update_donations_team.apply(kwargs={'teamID': self.team.id}, throw=True).result
        self.assertIsNone(result)
        mock_api.donations_for_team.assert_not_called()

    def test_creates_untracked_team_stub_when_team_not_in_db(self):
        mock_api = MagicMock()
        with patch.object(_donations_tasks, '_make_d', return_value=mock_api), \
                patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]):
            update_donations_team.apply(kwargs={'teamID': 99998}, throw=True)

        stub = TeamModel.objects.get(id=99998)
        self.assertFalse(stub.tracked)
        mock_api.donations_for_team.assert_not_called()


# ---------------------------------------------------------------------------
# update_donations_participant happy-path tests
# ---------------------------------------------------------------------------

class UpdateDonationsParticipantHappyPathTest(TestCase):
    def setUp(self):
        self.event = EventModel.objects.create(id=2026, tracked=True)
        self.participant = ParticipantModel.objects.create(
            id=12001, tracked=True, event=self.event
        )

    def _run(self, donations, participant_id=None):
        pid = participant_id if participant_id is not None else self.participant.id
        mock_api = MagicMock()
        mock_api.donations_for_participants.return_value = donations
        with patch.object(_donations_tasks, '_make_d', return_value=mock_api), \
                patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]), \
                patch.object(_donations_tasks, 'note_new_donation') as mock_note:
            result = update_donations_participant.apply(
                kwargs={'participant_id': pid}, throw=True
            ).result
        return result, mock_note

    def test_donation_is_saved_to_db_with_correct_fields(self):
        donation = _make_donation('PDON001', amount=15.0, display_name='Bob', message='Nice work!')
        self._run([donation])

        saved = DonationModel.objects.get(id='PDON001')
        self.assertEqual(saved.amount, 15.0)
        self.assertEqual(saved.displayName, 'Bob')
        self.assertEqual(saved.message, 'Nice work!')
        self.assertEqual(saved.participant, self.participant)

    def test_returns_list_of_guids(self):
        donation = _make_donation('PDON002')
        result, _ = self._run([donation])

        saved = DonationModel.objects.get(id='PDON002')
        self.assertEqual(result, [saved.guid])

    def test_note_new_donation_called_per_donation(self):
        donations = [_make_donation('PD1'), _make_donation('PD2')]
        _, mock_note = self._run(donations)

        self.assertEqual(mock_note.apply_async.call_count, 2)

    def test_null_display_name_saved_as_empty_string(self):
        donation = _make_donation('PDON003', display_name=None)
        self._run([donation])

        self.assertEqual(DonationModel.objects.get(id='PDON003').displayName, '')

    def test_null_message_saved_as_empty_string(self):
        donation = _make_donation('PDON004', message=None)
        self._run([donation])

        self.assertEqual(DonationModel.objects.get(id='PDON004').message, '')

    def test_unknown_team_stub_is_auto_created(self):
        donation = _make_donation('PDON005', team_id=66666)
        self._run([donation])

        team = TeamModel.objects.get(id=66666)
        self.assertFalse(team.tracked)

    def test_known_team_is_linked_without_creating_stub(self):
        existing_team = TeamModel.objects.create(id=66667, tracked=True, event=self.event)
        donation = _make_donation('PDON006', team_id=66667)
        self._run([donation])

        self.assertEqual(TeamModel.objects.filter(id=66667).count(), 1)
        self.assertEqual(DonationModel.objects.get(id='PDON006').team, existing_team)

    def test_existing_donation_is_updated_not_duplicated(self):
        DonationModel.objects.create(id='PDON007', participant=self.participant, amount=1.0)
        donation = _make_donation('PDON007', amount=50.0)
        self._run([donation])

        self.assertEqual(DonationModel.objects.filter(id='PDON007').count(), 1)
        self.assertEqual(DonationModel.objects.get(id='PDON007').amount, 50.0)

    def test_returns_empty_list_when_participant_id_is_none(self):
        mock_api = MagicMock()
        with patch.object(_donations_tasks, '_make_d', return_value=mock_api):
            result = update_donations_participant.apply(
                kwargs={'participant_id': None}, throw=True
            ).result
        self.assertEqual(result, [])
        mock_api.donations_for_participants.assert_not_called()

    def test_returns_empty_list_when_participant_not_tracked(self):
        self.participant.tracked = False
        self.participant.save()
        mock_api = MagicMock()
        with patch.object(_donations_tasks, '_make_d', return_value=mock_api), \
                patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]):
            result = update_donations_participant.apply(
                kwargs={'participant_id': self.participant.id}, throw=True
            ).result
        self.assertEqual(result, [])
        mock_api.donations_for_participants.assert_not_called()

    def test_creates_untracked_participant_stub_when_not_in_db(self):
        mock_api = MagicMock()
        with patch.object(_donations_tasks, '_make_d', return_value=mock_api), \
                patch.object(_donations_tasks, 'current_el_events', return_value=[self.event.id]):
            update_donations_participant.apply(kwargs={'participant_id': 99997}, throw=True)

        stub = ParticipantModel.objects.get(id=99997)
        self.assertFalse(stub.tracked)
        mock_api.donations_for_participants.assert_not_called()


# ---------------------------------------------------------------------------
# update_teams happy-path tests
# ---------------------------------------------------------------------------

from extralifeapi.teams import Team as _Team
from extralifeapi.participants import Participant as _Participant


def _make_team_namedtuple(team_id=8775, name='The Bonhams', event_id=508,
                          event_name='Test Event', fundraising_goal=20000.0,
                          num_donations=97, sum_donations=9349.5):
    data = {
        'teamID': team_id, 'name': name, 'avatarImageURL': 'https://example.com/avatar.gif',
        'createdDateUTC': '2026-01-01T00:00:00.000+0000', 'eventID': event_id,
        'eventName': event_name, 'fundraisingGoal': fundraising_goal,
        'numDonations': num_donations, 'sumDonations': sum_donations,
    }
    return _Team(**{f: data.get(f, None) for f in _Team._fields if f != 'raw'}, raw=data)


def _make_participant_namedtuple(participant_id=19265, display_name='Liam Bonham',
                                 event_id=508, team_id=8775, team_name='The Bonhams',
                                 is_team_captain=True, sum_donations=4661.0,
                                 num_donations=51, fundraising_goal=8000.0):
    data = {
        'participantID': participant_id, 'displayName': display_name, 'eventID': event_id,
        'eventName': 'Test Event', 'teamID': team_id, 'teamName': team_name,
        'isTeamCaptain': is_team_captain, 'sumDonations': sum_donations,
        'numDonations': num_donations, 'fundraisingGoal': fundraising_goal,
        'avatarImageURL': 'https://example.com/avatar.gif',
        'createdDateUTC': '2026-01-01T00:00:00.000+0000',
        'sumPledges': 0, 'campaignDate': None, 'campaignName': None,
    }
    return _Participant(**{f: data.get(f, None) for f in _Participant._fields if f != 'raw'}, raw=data)


@override_settings(EXTRALIFE_TEAMID=8775)
class UpdateTeamsHappyPathTest(TestCase):
    def setUp(self):
        self.event = EventModel.objects.create(id=508, tracked=True)

    def _run(self, teams_arg, api_teams):
        mock_api = MagicMock()
        mock_api.team.side_effect = api_teams
        with patch.object(_teams_tasks, '_make_team', return_value=mock_api), \
                patch.object(_donations_tasks, 'update_donations_if_needed_team') as mock_don:
            result = update_teams.apply(kwargs={'teams': teams_arg}, throw=True).result
        return result, mock_api, mock_don

    def test_team_fields_saved_to_db(self):
        team = _make_team_namedtuple()
        self._run([8775], [team])

        saved = TeamModel.objects.get(id=8775)
        self.assertEqual(saved.name, 'The Bonhams')
        self.assertEqual(saved.numDonations, 97)
        self.assertEqual(saved.sumDonations, 9349.5)
        self.assertEqual(saved.fundraisingGoal, 20000.0)
        self.assertEqual(saved.event, self.event)

    def test_returns_list_of_guids(self):
        team = _make_team_namedtuple()
        result, _, _ = self._run([8775], [team])

        saved = TeamModel.objects.get(id=8775)
        self.assertEqual(result, [saved.guid])

    def test_sets_tracked_true_for_extralife_team_id(self):
        team = _make_team_namedtuple(team_id=8775)
        self._run([8775], [team])

        self.assertTrue(TeamModel.objects.get(id=8775).tracked)

    def test_does_not_set_tracked_for_other_team(self):
        team = _make_team_namedtuple(team_id=9999, event_id=508)
        self._run([9999], [team])

        self.assertFalse(TeamModel.objects.get(id=9999).tracked)

    def test_creates_event_stub_when_event_not_in_db(self):
        # Event 999 doesn't exist - should be auto-created as untracked
        team = _make_team_namedtuple(event_id=999, event_name='Unknown Event')
        self._run([8775], [team])

        evt = EventModel.objects.get(id=999)
        self.assertFalse(evt.tracked)

    def test_links_existing_event_without_creating_stub(self):
        team = _make_team_namedtuple(event_id=508)
        self._run([8775], [team])

        self.assertEqual(EventModel.objects.filter(id=508).count(), 1)

    def test_queues_donations_update_for_tracked_team(self):
        team = _make_team_namedtuple(team_id=8775)
        _, _, mock_don = self._run([8775], [team])

        mock_don.delay.assert_called_once_with(teamID=8775)

    def test_does_not_queue_donations_for_untracked_team(self):
        team = _make_team_namedtuple(team_id=9999, event_id=508)
        _, _, mock_don = self._run([9999], [team])

        mock_don.delay.assert_not_called()

    def test_updates_existing_team_in_place(self):
        TeamModel.objects.create(id=8775, tracked=False, name='Old Name')
        team = _make_team_namedtuple(team_id=8775, name='New Name')
        self._run([8775], [team])

        self.assertEqual(TeamModel.objects.filter(id=8775).count(), 1)
        self.assertEqual(TeamModel.objects.get(id=8775).name, 'New Name')

    def test_uses_extralife_teamid_when_teams_arg_is_none(self):
        team = _make_team_namedtuple(team_id=8775)
        mock_api = MagicMock()
        mock_api.team.return_value = team
        with patch.object(_teams_tasks, '_make_team', return_value=mock_api), \
                patch.object(_donations_tasks, 'update_donations_if_needed_team'):
            update_teams.apply(kwargs={'teams': None}, throw=True)

        mock_api.team.assert_called_once_with(teamID=8775)

    def test_team_with_no_event_gets_null_event(self):
        team = _make_team_namedtuple(event_id=None)
        self._run([8775], [team])

        self.assertIsNone(TeamModel.objects.get(id=8775).event)


# ---------------------------------------------------------------------------
# update_participants happy-path tests
# ---------------------------------------------------------------------------

@override_settings(EXTRALIFE_TEAMID=8775)
class UpdateParticipantsHappyPathTest(TestCase):
    def setUp(self):
        self.event = EventModel.objects.create(id=508, tracked=True)
        self.team = TeamModel.objects.create(id=8775, tracked=True, event=self.event)

    def _run(self, participants_arg, api_participants):
        mock_api = MagicMock()
        if participants_arg is None:
            mock_api.participants_for_team.return_value = api_participants
        else:
            mock_api.participant.side_effect = api_participants
        with patch.object(_participants_tasks, '_make_p', return_value=mock_api), \
                patch.object(_donations_tasks, 'update_donations_if_needed_participant') as mock_dp, \
                patch.object(_donations_tasks, 'update_donations_if_needed_team') as mock_dt:
            result = update_participants.apply(kwargs={'participants': participants_arg}, throw=True).result
        return result, mock_api, mock_dp, mock_dt

    def test_participant_fields_saved_to_db(self):
        p = _make_participant_namedtuple()
        self._run(None, [p])

        saved = ParticipantModel.objects.get(id=19265)
        self.assertEqual(saved.displayName, 'Liam Bonham')
        self.assertEqual(saved.numDonations, 51)
        self.assertEqual(saved.sumDonations, 4661.0)
        self.assertEqual(saved.fundraisingGoal, 8000.0)
        self.assertEqual(saved.event, self.event)
        self.assertEqual(saved.team, self.team)

    def test_returns_list_of_guids(self):
        p = _make_participant_namedtuple()
        result, _, _, _ = self._run(None, [p])

        saved = ParticipantModel.objects.get(id=19265)
        self.assertEqual(result, [saved.guid])

    def test_promotes_tracked_when_event_is_tracked(self):
        # Participant starts untracked but event is tracked - should be promoted
        p = _make_participant_namedtuple(team_id=None)
        self._run(None, [p])

        self.assertTrue(ParticipantModel.objects.get(id=19265).tracked)

    def test_promotes_tracked_when_team_is_tracked(self):
        p = _make_participant_namedtuple(event_id=None)
        self._run(None, [p])

        self.assertTrue(ParticipantModel.objects.get(id=19265).tracked)

    def test_stays_untracked_when_neither_event_nor_team_is_tracked(self):
        untracked_event = EventModel.objects.create(id=999, tracked=False)
        TeamModel.objects.create(id=9999, tracked=False, event=untracked_event)
        p = _make_participant_namedtuple(event_id=999, team_id=9999, team_name='Untracked')
        self._run(None, [p])

        self.assertFalse(ParticipantModel.objects.get(id=19265).tracked)

    def test_queues_donation_updates_for_tracked_participant(self):
        p = _make_participant_namedtuple()
        _, _, mock_dp, mock_dt = self._run(None, [p])

        mock_dp.delay.assert_called_once_with(participantID=19265)
        mock_dt.delay.assert_called_once_with(teamID=8775)

    def test_does_not_queue_donation_updates_for_untracked_participant(self):
        untracked_event = EventModel.objects.create(id=999, tracked=False)
        TeamModel.objects.create(id=9999, tracked=False, event=untracked_event)
        p = _make_participant_namedtuple(event_id=999, team_id=9999, team_name='Untracked')
        _, _, mock_dp, mock_dt = self._run(None, [p])

        mock_dp.delay.assert_not_called()
        mock_dt.delay.assert_not_called()

    def test_creates_event_stub_when_event_not_in_db(self):
        p = _make_participant_namedtuple(event_id=777)
        self._run(None, [p])

        evt = EventModel.objects.get(id=777)
        self.assertFalse(evt.tracked)

    def test_creates_team_stub_when_team_not_in_db(self):
        p = _make_participant_namedtuple(team_id=5555, team_name='New Team')
        self._run(None, [p])

        team = TeamModel.objects.get(id=5555)
        self.assertFalse(team.tracked)
        self.assertEqual(team.name, 'New Team')

    def test_updates_existing_participant_in_place(self):
        ParticipantModel.objects.create(id=19265, tracked=False, displayName='Old Name')
        p = _make_participant_namedtuple(display_name='New Name')
        self._run(None, [p])

        self.assertEqual(ParticipantModel.objects.filter(id=19265).count(), 1)
        self.assertEqual(ParticipantModel.objects.get(id=19265).displayName, 'New Name')

    def test_fetches_individual_participants_when_ids_provided(self):
        p = _make_participant_namedtuple()
        _, mock_api, _, _ = self._run([19265], [p])

        mock_api.participant.assert_called_once_with(19265)
        mock_api.participants_for_team.assert_not_called()


# ---------------------------------------------------------------------------
# note_new_donation / note_new_donations sender tests
# ---------------------------------------------------------------------------

_sender_tasks = importlib.import_module('ffdonations.tasks.sender')

from .tasks.sender import note_new_donation, note_new_donations


@override_settings(
    FRAG_BOT_KEY='testkey',
    FRAG_BOT_API='https://bot.example.com/dbquery',
    FRAG_BOT_BOT='testbot',
)
class NoteNewDonationTest(TestCase):
    def setUp(self):
        self.donation = DonationModel.objects.create(
            id='SEND001',
            amount=25.00,
            displayName='Alice',
            message='Keep it up!',
        )

    def _run(self, donation_id=None):
        did = donation_id if donation_id is not None else self.donation.id
        with patch.object(_sender_tasks, 'requests') as mock_requests:
            mock_requests.put.return_value = MagicMock()
            note_new_donation.apply(args=[did], throw=True)
        return mock_requests

    @override_settings(FRAG_BOT_KEY='')
    def test_marks_tracked_without_sending_when_no_bot_key(self):
        with patch.object(_sender_tasks, 'requests') as mock_requests:
            note_new_donation.apply(args=[self.donation.id], throw=True)

        mock_requests.put.assert_not_called()
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.tracking.get('TRACKING_BOT'), '1')

    def test_skips_already_tracked_donation(self):
        self.donation.tracking['TRACKING_BOT'] = '1'
        self.donation.tracking = self.donation.tracking.copy()
        self.donation.save()

        mock_requests = self._run()

        mock_requests.put.assert_not_called()

    def test_makes_two_put_requests(self):
        mock_requests = self._run()

        self.assertEqual(mock_requests.put.call_count, 2)

    def test_first_put_message_includes_amount(self):
        mock_requests = self._run()

        first_payload = mock_requests.put.call_args_list[0][1]['headers']
        self.assertIn(b'$25.0', first_payload['message'])

    def test_first_put_message_includes_named_donor(self):
        mock_requests = self._run()

        first_payload = mock_requests.put.call_args_list[0][1]['headers']
        self.assertIn(b'Alice', first_payload['message'])

    def test_first_put_message_uses_anonymous_coward_when_no_display_name(self):
        self.donation.displayName = ''
        self.donation.save()

        mock_requests = self._run()

        first_payload = mock_requests.put.call_args_list[0][1]['headers']
        self.assertIn(b'Anonymous Coward', first_payload['message'])

    def test_first_put_message_includes_donor_message(self):
        mock_requests = self._run()

        first_payload = mock_requests.put.call_args_list[0][1]['headers']
        self.assertIn(b'Keep it up!', first_payload['message'])

    def test_first_put_message_omits_message_section_when_no_message(self):
        self.donation.message = ''
        self.donation.save()

        mock_requests = self._run()

        first_payload = mock_requests.put.call_args_list[0][1]['headers']
        self.assertNotIn(b'with the message', first_payload['message'])

    def test_second_put_sends_bot_donate_command(self):
        mock_requests = self._run()

        second_payload = mock_requests.put.call_args_list[1][1]['headers']
        self.assertEqual(second_payload['message'], '!bot_donate')

    def test_marks_tracking_after_successful_send(self):
        self._run()

        self.donation.refresh_from_db()
        self.assertEqual(self.donation.tracking.get('TRACKING_BOT'), '1')

    def test_both_puts_use_configured_api_url(self):
        mock_requests = self._run()

        for call_args in mock_requests.put.call_args_list:
            self.assertEqual(call_args[0][0], 'https://bot.example.com/dbquery')


class NoteNewDonationsTest(TestCase):
    def test_queues_note_for_each_untracked_donation(self):
        DonationModel.objects.create(id='UNSENT1', amount=10.0)
        DonationModel.objects.create(id='UNSENT2', amount=20.0)

        with patch.object(_sender_tasks, 'note_new_donation') as mock_task:
            note_new_donations.apply(throw=True)

        self.assertEqual(mock_task.apply_async.call_count, 2)

    def test_skips_already_tracked_donations(self):
        DonationModel.objects.create(id='SENT1', amount=10.0, tracking={'TRACKING_BOT': '1'})
        DonationModel.objects.create(id='UNSENT3', amount=20.0)

        with patch.object(_sender_tasks, 'note_new_donation') as mock_task:
            note_new_donations.apply(throw=True)

        mock_task.apply_async.assert_called_once_with(('UNSENT3',), queue='alerts')


from ffdonations.views.donations import VALID_ORDER_FIELDS


class DonationViewOrderByWhitelistTest(TestCase):
    def setUp(self):
        event = EventModel.objects.create(id=1, name='Test Event')
        team = TeamModel.objects.create(id=73149, name='Fragforce', event=event, tracked=True)
        DonationModel.objects.create(id='D1', amount=50.0, team=team, created=timezone.now())
        DonationModel.objects.create(id='D2', amount=100.0, team=team, created=timezone.now() - timedelta(hours=1))

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_all_valid_orderby_fields_accepted(self, mock_task):
        for field in VALID_ORDER_FIELDS:
            response = self.client.get(f'/d/donations?orderBy={field}')
            self.assertEqual(response.status_code, 200, f'orderBy={field} should be accepted')

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_invalid_orderby_falls_back_to_id(self, mock_task):
        response = self.client.get('/d/donations?orderBy=raw')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        ids = [d['id'] for d in data]
        self.assertEqual(ids, sorted(ids))

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_traversal_orderby_rejected(self, mock_task):
        response = self.client.get('/d/donations?orderBy=team__raw')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        ids = [d['id'] for d in data]
        self.assertEqual(ids, sorted(ids))

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_tracked_donations_invalid_orderby(self, mock_task):
        response = self.client.get('/d/donations/tracked?orderBy=team__raw')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        ids = [d['id'] for d in data]
        self.assertEqual(ids, sorted(ids))

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_tracked_donations_valid_fields_accepted(self, mock_task):
        for field in VALID_ORDER_FIELDS:
            response = self.client.get(f'/d/donations/tracked?orderBy={field}')
            self.assertEqual(response.status_code, 200, f'tracked orderBy={field} should be accepted')


class DonationViewRecordCountTest(TestCase):
    def setUp(self):
        event = EventModel.objects.create(id=1, name='Test Event')
        team = TeamModel.objects.create(id=73149, name='Fragforce', event=event, tracked=True)
        for i in range(3):
            DonationModel.objects.create(id=f'RC{i:02d}', amount=10.0, team=team, created=timezone.now())

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_invalid_recordcount_falls_back_to_full_list(self, mock_task):
        # Non-integer recordCount used to raise ValueError (500) - now falls back to 0
        response = self.client.get('/d/donations?recordCount=abc')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 3)

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_negative_recordcount_falls_back_to_full_list(self, mock_task):
        # Negative recordCount is out of range - falls back to the full list
        response = self.client.get('/d/donations?recordCount=-5')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 3)

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_valid_recordcount_limits_rows(self, mock_task):
        response = self.client.get('/d/donations?recordCount=2')
        data = response.json()
        self.assertEqual(len(data), 2)

    @override_settings(MAX_API_ROWS=2)
    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_recordcount_above_max_is_capped(self, mock_task):
        # recordCount > MAX_API_ROWS falls back to the MAX_API_ROWS slice
        response = self.client.get('/d/donations?recordCount=10')
        data = response.json()
        self.assertEqual(len(data), 2)


class DonationViewFilterByTest(TestCase):
    def setUp(self):
        event = EventModel.objects.create(id=1, name='Test Event')
        team = TeamModel.objects.create(id=73149, name='Fragforce', event=event, tracked=True)
        self.participant = ParticipantModel.objects.create(
            id=5001, displayName='Alice', event=event, tracked=True
        )
        other = ParticipantModel.objects.create(
            id=5002, displayName='Bob', event=event, tracked=True
        )
        DonationModel.objects.create(id='FB01', amount=10.0, team=team, participant=self.participant, created=timezone.now())
        DonationModel.objects.create(id='FB02', amount=20.0, team=team, participant=other, created=timezone.now())

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_digit_filterby_filters_to_participant(self, mock_task):
        response = self.client.get('/d/donations?filterBy=5001')
        data = response.json()
        self.assertEqual([d['id'] for d in data], ['FB01'])

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_non_digit_filterby_treated_as_none(self, mock_task):
        # Non-digit filterBy used to crash the queryset - now ignored
        response = self.client.get('/d/donations?filterBy=abc')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_negative_filterby_treated_as_none(self, mock_task):
        # '-5' isn't a digit - treated as none
        response = self.client.get('/d/donations?filterBy=-5')
        data = response.json()
        self.assertEqual(len(data), 2)

    @patch('ffdonations.views.donations.update_donations_if_needed')
    def test_none_filterby_returns_all(self, mock_task):
        response = self.client.get('/d/donations?filterBy=none')
        data = response.json()
        self.assertEqual(len(data), 2)
