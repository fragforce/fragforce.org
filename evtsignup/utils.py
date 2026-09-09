"""
Utilities for the evtsignup app.
"""
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


@dataclass
class FundraisingUrlResult:
    type: str       # 'participant', 'team', 'other', 'empty'
    id_or_slug: str  # extracted identifier, or original URL for 'other'
    raw_url: str    # always the original input

    @property
    def is_extralife(self):
        return self.type in ('participant', 'team')

    @property
    def is_participant(self):
        return self.type == 'participant'

    @property
    def is_team(self):
        return self.type == 'team'





def parse_fundraising_url(url: str) -> FundraisingUrlResult:
    """
    Parse a fundraising URL submitted on the signup form.

    Returns a FundraisingUrlResult indicating the type and extracted identifier.

    Examples:
        https://www.extra-life.org/participants/511438        → type='participant', id_or_slug='511438'
        https://www.extra-life.org/participants/aevumdecessus → type='participant', id_or_slug='aevumdecessus'
        https://www.extra-life.org/index.cfm?...participantID=511438 → type='participant', id_or_slug='511438'
        https://www.extra-life.org/teams/fragforce-dcm        → type='team', id_or_slug='fragforce-dcm'
        https://tiltify.com/+fragforce/                       → type='other', id_or_slug=url
        "I have not signed up yet"                            → type='other', id_or_slug=raw
        ''                                                    → type='empty', id_or_slug=''
    """
    raw = url.strip() if url else ''

    if not raw:
        return FundraisingUrlResult(type='empty', id_or_slug='', raw_url=raw)

    try:
        parsed = urlparse(raw if '://' in raw else f'https://{raw}')
    except Exception:
        return FundraisingUrlResult(type='other', id_or_slug=raw, raw_url=raw)

    host = parsed.netloc.lower()
    if host.startswith('www.'):
        host = host[4:]
    if host not in ('extra-life.org', 'donordrive.com'):
        return FundraisingUrlResult(type='other', id_or_slug=raw, raw_url=raw)

    path = parsed.path.rstrip('/')

    # Modern path format: /participants/{id_or_slug} or /teams/{id_or_slug}
    participant_match = re.match(r'^/participants/([^/]+)$', path, re.IGNORECASE)
    if participant_match:
        return FundraisingUrlResult(type='participant', id_or_slug=participant_match.group(1), raw_url=raw)

    team_match = re.match(r'^/teams/([^/]+)$', path, re.IGNORECASE)
    if team_match:
        return FundraisingUrlResult(type='team', id_or_slug=team_match.group(1), raw_url=raw)

    # Legacy cfm format: ?fuseaction=donorDrive.participant&participantID=12345
    # or ?fuseaction=donorDrive.team&teamID=12345
    # Also handles ?fuseaction=portal.home&participantID=12345 (seen in practice)
    qs = parse_qs(parsed.query)

    participant_id = (qs.get('participantID') or qs.get('participantid') or [None])[0]
    if participant_id:
        return FundraisingUrlResult(type='participant', id_or_slug=participant_id, raw_url=raw)

    team_id = (qs.get('teamID') or qs.get('teamid') or [None])[0]
    if team_id:
        return FundraisingUrlResult(type='team', id_or_slug=team_id, raw_url=raw)

    # EL URL but unrecognised format - store as other
    return FundraisingUrlResult(type='other', id_or_slug=raw, raw_url=raw)
