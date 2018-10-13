import requests
import os


def is_active(endpoint=None, section=None, noclass=False, sfid=None):
    # FIXME: Handle sfid to check if it's a real, active page
    rtn = ""
    if noclass:
        rtn = 'active'
    else:
        rtn = 'class=active'
    if endpoint and section:
        if 'section' in request.view_args:
            if request.url_rule.endpoint == endpoint and request.view_args['section'] == section:
                return rtn
    elif endpoint:
        return rtn if request.url_rule.endpoint == endpoint else ''
    elif section:
        if 'section' in request.view_args:
            return rtn if request.view_args['section'] == section else ''
    return ''


def print_bar(goal, total, percent, label):
    return '   <div>' + \
           '     <div class="progress-text">' + \
           '       <span class="label">' + str(label) + '</span>' + \
           '     </div>' + \
           '     <div class="progress-amount">' + \
           '       <span class="label"> $' + u'{:0,.0f}'.format(float(total)) + ' &#47; $' + u'{:0,.0f}'.format(
        float(goal)) + '</span>' + \
           '     </div>' + \
           '   </div>' + \
           '   <div class="progress">' + \
           '     <div class="progress-bar" role="progressbar" aria-valuenow="60" aria-valuemin="0" ' \
           'aria-valuemax="100" style="' + str(
        percent) + '%; max-width: ' + str(percent) + '%; min-width: 2em; width: ' + str(percent) + '%;">' + \
           '     ' + str(percent) + '% ' + \
           '     </div>' + \
           '   </div>'


def print_bars():
    extralife_total = 0
    extralife_goal = 0
    extralife_percent = 0
    childsplay_total = 0
    childsplay_goal = 0
    childsplay_percent = 0
    full_total = 0
    full_goal = 0
    full_percent = 0
    try:
        r = requests.get('https://extra-life.org/api/teams/38642')
        if r.status_code == 200:
            data = r.json()
            extralife_total = data['sumDonations']
            extralife_goal = data['fundraisingGoal']

        if extralife_goal > 0:
            extralife_percent = u'{:0,.2f}'.format(100 * (extralife_total / extralife_goal))

    except extralife.WebServiceException as e:
        fail = True
    try:
        r = requests.get('https://tiltify.com/api/v2/campaign',
                         headers={'Authorization': 'Token 8b41dcba5ff2cc228e69ef3a31e94bd1'
                                  })
        if r.status_code == 200:
            data = r.json()
            childsplay_total = data['total_raised']
            childsplay_goal = data['goal']
            childsplay_percent = data['percent_raised'].rstrip("%")
    except requests.exceptions.RequestException as e:
        fail = True
    full_total = extralife_total + childsplay_total
    full_goal = extralife_goal + childsplay_goal
    if full_goal > 0:
        full_percent = u'{:0,.2f}'.format(100 * (full_total / full_goal))
    else:
        full_percent = 0
    return print_bar(extralife_goal, extralife_total, extralife_percent, "Extra Life") + \
           print_bar(childsplay_goal, childsplay_total, childsplay_percent, "Childs Play") + \
           print_bar(full_goal, full_total, full_percent, "Totals")


