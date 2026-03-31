from datetime import timedelta
from unittest.mock import call, patch
from urllib.parse import urlparse

from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from .admin import ParticipantModelAdmin, TeamModelAdmin
from .helpers import el_request_sleeper
from .models import ParticipantModel, TeamModel


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
