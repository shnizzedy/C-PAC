# Copyright (C) 2018-2024  C-PAC Developers

# This file is part of C-PAC.

# C-PAC is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.

# C-PAC is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with C-PAC. If not, see <https://www.gnu.org/licenses/>.
import configparser
import os
import os.path as op
import tempfile
import threading
import traceback
import uuid

import requests

from CPAC.info import __version__, ga_tracker

temp_dir = False
udir = op.expanduser("~")
if udir == "/":
    udir = tempfile.mkdtemp()
    temp_dir = True
tracking_path = op.join(udir, ".cpac")


def get_or_create_config():
    if not op.exists(tracking_path):
        parser = configparser.ConfigParser()
        parser.read_dict({"user": {"uid": uuid.uuid1().hex, "track": True}})
        with open(tracking_path, "w+") as fhandle:
            parser.write(fhandle)
    else:
        parser = configparser.ConfigParser()
        parser.read(tracking_path)

    return parser


def get_uid():
    if os.environ.get("CPAC_TRACKING", "").lower() not in ["", "0", "false", "off"]:
        return os.environ.get("CPAC_TRACKING")

    parser = get_or_create_config()
    if parser["user"].getboolean("track"):
        return parser["user"]["uid"]

    return None


def do_it(data, timeout):
    try:
        headers = {"User-Agent": f"C-PAC/{__version__} (https://fcp-indi.github.io)"}
        _done = requests.post(
            "https://www.google-analytics.com/collect",
            data=data,
            timeout=timeout,
            headers=headers,
        )
    except:
        _done = False
    finally:
        if temp_dir:
            try:
                os.remove(tracking_path)
                os.rmdir(udir)
            except (TypeError, OSError) as e:
                msg = f"Unable to delete temporary tracking path {tracking_path}."
                raise OSError(msg) from e
        return _done


def track_event(
    category,
    action,
    uid=None,
    label=None,
    value=0,
    software_version=None,
    timeout=2,
    thread=True,
):
    """
    Record an event with Google Analytics.

    Parameters
    ----------
    tracking_id : str
        Google Analytics tracking ID.
    category : str
        Event category.
    action : str
        Event action.
    uid : str
        User unique ID, assigned when popylar was installed.
    label : str
        Event label.
    value : int
        Event value.
    software_version : str
        Records a version of the software.
    timeout : float
        Maximal duration (in seconds) for the network connection to track the
        event. After this duration has elapsed with no response (e.g., on a
        slow network connection), the tracking is dropped.
    """
    if os.environ.get("CPAC_TRACKING", "").lower() in ["0", "false", "off"]:
        return

    if uid is None:
        uid = get_uid()

    if not uid:
        return

    this = "/CPAC/utils/ga.py"
    exec_stack = list(reversed(traceback.extract_stack()))
    assert exec_stack[0][0].endswith(this)
    package_path = exec_stack[0][0][: -len(this)]

    # only CPAC paths are going to be recorded
    file_path = ""
    for s in exec_stack:
        if s[0].endswith(this):
            continue
        if not s[0].startswith(package_path):
            break
        file_path = s[0][len(package_path) :]

    data = {
        "v": "1",  # API version.
        "tid": ga_tracker,  # GA tracking ID
        "dp": file_path,
        "cid": uid,  # User unique ID, stored in `tracking_path`
        "t": "event",  # Event hit type.
        "ec": category,  # Event category.
        "ea": action,  # Event action.
        "el": label,  # Event label.
        "ev": value,  # Event value, must be an integer
        "aid": "CPAC",
        "an": "CPAC",
        "av": __version__,
        "aip": 1,  # anonymize IP by removing last octet, slightly worse
        # geolocation
    }

    if thread:
        t = threading.Thread(target=do_it, args=(data, timeout))
        t.start()
    else:
        do_it(data, timeout)


def track_config(cpac_interface):
    track_event("config", cpac_interface, label=None, value=None, thread=False)


def track_run(level="participant", participants=0):
    if level in ["participant", "group"]:
        track_event(
            "run", level, label="participants", value=participants, thread=False
        )
    else:
        track_event(
            "config", "test", label="participants", value=participants, thread=False
        )
