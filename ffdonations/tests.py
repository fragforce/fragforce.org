import importlib
from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from requests.exceptions import HTTPError

from .admin import ParticipantModelAdmin, TeamModelAdmin
from .helpers import el_request_sleeper
from .models import EventModel, ParticipantModel, TeamModel
from .tasks.donations import update_donations_participant, update_donations_team
from .tasks.participants import update_participants
from .tasks.teams import update_teams

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
        team1 = TeamModel.objects.create(id=1001)
        team2 = TeamModel.objects.create(id=1002)
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
        p1 = ParticipantModel.objects.create(id=2001)
        p2 = ParticipantModel.objects.create(id=2002)
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
