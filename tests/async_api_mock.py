REEF_MOCK_URL = "http://192.168.1.123"
REEF_MOCK_USER = "reef_pi"
REEF_MOCK_PASSWORD = "reef_password"


def mock_signin(mock, url=REEF_MOCK_URL):
    mock.post(f"{url}/auth/signin").respond(200, headers={"set-cookie": "auth=token"})


def mock_capabilities(mock, ph=True, url=REEF_MOCK_URL):
    mock.get(f"{url}/api/capabilities", cookies={"auth": "token"}).respond(
        200,
        json={
            "dev_mode": False,
            "dashboard": False,
            "health_check": False,
            "equipment": True,
            "timers": False,
            "lighting": True,
            "temperature": True,
            "ato": True,
            "camera": False,
            "doser": True,
            "ph": ph,
            "macro": False,
            "configuration": False,
            "journal": False,
        },
    )


def mock_phprobes(mock, url=REEF_MOCK_URL):
    mock.get(f"{url}/api/phprobes").respond(
        200,
        json=[
            {
                "id": "6",
                "name": "pH",
                "enable": True,
                "period": 15,
                "analog_input": "1",
                "control": True,
                "notify": {"enable": True, "min": 7.5, "max": 8.6},
                "upper_eq": "10",
                "downer_eq": "9",
                "min": 8.1,
                "max": 8.25,
                "hysteresis": 0.1,
                "is_macro": False,
                "one_shot": False,
                "chart": {"ymin": 0, "ymax": 0, "color": "", "unit": ""},
            },
            {
                "id": "7",
                "name": "pH No current",
                "enable": True,
            },
            {
                "id": "8",
                "name": "pH No history",
                "enable": True,
            },
        ],
    )


def mock_ph6(mock, url=REEF_MOCK_URL):
    mock.get(f"{url}/api/phprobes/6/read").respond(200, json="6.31")


def mock_ph78(mock, url=REEF_MOCK_URL):
    mock.get(f"{url}/api/phprobes/7/read").respond(200, json="7.23")
    mock.get(f"{url}/api/phprobes/8/read").respond(200, json="")


def mock_info(mock, url=REEF_MOCK_URL):
    mock.get(f"{url}/api/info").respond(
        200,
        json={
            "name": "Reef PI",
            "ip": "192.168.1.123",
            "current_time": "Sat Jun 12 22:05:32",
            "uptime": "1 week ago",
            "cpu_temperature": "39.0'C\n",
            "version": "4.1",
            "model": "Raspberry Pi 2 Model B Rev 1.1\x00",
        },
    )


def mock_atos(mock, url=REEF_MOCK_URL, empty_usage=False):
    mock.get(f"{url}/api/atos").respond(
        200,
        json=[
            {
                "id": "1",
                "is_macro": False,
                "inlet": "2",
                "pump": "1",
                "period": 120,
                "control": True,
                "enable": True,
                "notify": {"enable": False, "max": 0},
                "name": "Test ATO",
                "disable_on_alert": False,
                "one_shot": False,
            }
        ],
    )

    if empty_usage:
        mock.get(f"{url}/api/atos/1/usage").respond(200, json={})
    else:
        mock.get(f"{url}/api/atos/1/usage").respond(
            200,
            json={
                "current": [
                    {"pump": 120, "time": "Jan-11-09:01, 2022"},
                    {"pump": 0, "time": "Jan-12-09:01, 2022"},
                ]
            },
        )


def mock_lights(mock, url=REEF_MOCK_URL):
    mock.get(f"{url}/api/lights").respond(
        200,
        json=[
            {
                "id": "1",
                "channels": {
                    "red": {
                        "manual": True,
                        "name": "Red",
                        "value": 0.5,
                    }
                },
                "name": "ReefPi Light",
            },
        ],
    )


def mock_all(mock, url=REEF_MOCK_URL, has_ph=True, has_ato_usage=True):
    mock_signin(mock)
    mock_capabilities(mock)
    mock_info(mock)
    mock_phprobes(mock)
    mock_ph6(mock)
    mock_ph78(mock)
    mock_atos(mock, empty_usage=not has_ato_usage)
    mock_lights(mock)

    mock.get(f"{url}/api/doser/pumps").respond(
        200,
        json=[
            {
                "id": "1",
                "name": "Pump1 sched1",
                "jack": "1",
                "pin": 0,
                "regiment": {
                    "enable": True,
                    "schedule": {
                        "day": "*",
                        "hour": "19",
                        "minute": "30",
                        "second": "0",
                        "week": "*",
                        "month": "*",
                    },
                    "duration": 15,
                    "speed": 20,
                },
            },
            {
                "id": "2",
                "name": "Pump1 sched2",
                "jack": "1",
                "pin": 0,
                "regiment": {
                    "enable": True,
                    "schedule": {
                        "day": "*",
                        "hour": "20",
                        "minute": "30",
                        "second": "0",
                        "week": "*",
                        "month": "*",
                    },
                    "duration": 15,
                    "speed": 20,
                },
            },
            {
                "id": "3",
                "name": "Pump2 sched1",
                "jack": "2",
                "pin": 1,
                "regiment": {
                    "enable": True,
                    "schedule": {
                        "day": "*",
                        "hour": "21",
                        "minute": "30",
                        "second": "0",
                        "week": "*",
                        "month": "*",
                    },
                    "duration": 15,
                    "speed": 20,
                },
            },
            {
                "id": "4",
                "name": "Pump2 sched1",
                "jack": "2",
                "pin": 2,
                "regiment": {
                    "enable": True,
                    "schedule": {
                        "day": "*",
                        "hour": "22",
                        "minute": "30",
                        "second": "0",
                        "week": "*",
                        "month": "*",
                    },
                    "duration": 15,
                    "speed": 20,
                },
            },
            {
                "id": "5",
                "name": "No history",
                "jack": "3",
                "pin": 0,
                "regiment": {
                    "enable": True,
                    "schedule": {
                        "day": "*",
                        "hour": "22",
                        "minute": "30",
                        "second": "0",
                        "week": "*",
                        "month": "*",
                    },
                    "duration": 15,
                    "speed": 20,
                },
            },
        ],
    )

    mock.get(f"{url}/api/doser/pumps/1/usage").respond(
        200,
        json={
            "current": [
                {"pump": 11, "time": "Aug-18-14:05, 2021"},
                {"pump": 15, "time": "Aug-18-19:30, 2021"},
                {"pump": 15, "time": "Aug-19-19:30, 2021"},
                {"pump": 15, "time": "Aug-20-19:30, 2021"},
                {"pump": 15, "time": "Aug-21-19:30, 2021"},
                {"pump": 15, "time": "Aug-22-19:30, 2021"},
                {"pump": 15, "time": "Aug-23-19:30, 2021"},
            ],
            "historical": [
                {"pump": 26, "time": "Aug-18-14:05, 2021"},
                {"pump": 15, "time": "Aug-19-19:30, 2021"},
                {"pump": 15, "time": "Aug-20-19:30, 2021"},
                {"pump": 15, "time": "Aug-21-19:30, 2021"},
                {"pump": 15, "time": "Aug-22-19:30, 2021"},
                {"pump": 15, "time": "Aug-23-19:30, 2021"},
            ],
        },
    )

    mock.get(f"{url}/api/doser/pumps/2/usage").respond(
        200,
        json={
            "current": [
                {"pump": 11, "time": "Aug-18-14:05, 2021"},
                {"pump": 15, "time": "Aug-18-19:30, 2021"},
                {"pump": 15, "time": "Aug-19-19:30, 2021"},
                {"pump": 15, "time": "Aug-20-19:30, 2021"},
                {"pump": 15, "time": "Aug-21-19:30, 2021"},
                {"pump": 15, "time": "Aug-22-19:30, 2021"},
                {"pump": 15, "time": "Aug-23-20:30, 2021"},
            ],
            "historical": [
                {"pump": 26, "time": "Aug-18-14:05, 2021"},
                {"pump": 15, "time": "Aug-19-19:30, 2021"},
                {"pump": 15, "time": "Aug-20-19:30, 2021"},
                {"pump": 15, "time": "Aug-21-19:30, 2021"},
                {"pump": 15, "time": "Aug-22-21:30, 2021"},
            ],
        },
    )

    mock.get(f"{url}/api/doser/pumps/3/usage").respond(
        200,
        json={
            "current": [
                {"pump": 11, "time": "Aug-18-14:05, 2021"},
                {"pump": 15, "time": "Aug-18-19:30, 2021"},
                {"pump": 15, "time": "Aug-19-19:30, 2021"},
                {"pump": 15, "time": "Aug-20-19:30, 2021"},
                {"pump": 15, "time": "Aug-21-19:30, 2021"},
                {"pump": 15, "time": "Aug-23-21:30, 2021"},
            ],
            "historical": [
                {"pump": 26, "time": "Aug-18-14:05, 2021"},
                {"pump": 15, "time": "Aug-19-19:30, 2021"},
                {"pump": 15, "time": "Aug-20-19:30, 2021"},
                {"pump": 15, "time": "Aug-21-19:30, 2021"},
                {"pump": 15, "time": "Aug-22-19:30, 2021"},
                {"pump": 15, "time": "Aug-23-22:30, 2021"},
            ],
        },
    )

    mock.get(f"{url}/api/doser/pumps/4/usage").respond(
        200,
        json={
            "historical": [
                {"pump": 26, "time": "Aug-18-14:05, 2021"},
                {"pump": 15, "time": "Aug-19-19:30, 2021"},
                {"pump": 15, "time": "Aug-20-19:30, 2021"},
                {"pump": 15, "time": "Aug-21-19:30, 2021"},
                {"pump": 15, "time": "Aug-22-19:30, 2021"},
                {"pump": 15, "time": "Aug-23-19:30, 2021"},
            ]
        },
    )

    mock.get(f"{url}/api/doser/pumps/5/usage").respond(200, json={})

    mock.get(f"{url}/api/equipment").respond(
        200,
        json=[
            {
                "id": "1",
                "name": "Old light",
                "outlet": "1",
                "on": True,
                "stay_off_on_boot": False,
            },
            {
                "id": "17",
                "name": "Led light 1",
                "outlet": "17",
                "on": False,
                "stay_off_on_boot": False,
            },
            {
                "id": "18",
                "name": "Led light 2",
                "outlet": "18",
                "on": True,
                "stay_off_on_boot": False,
            },
            {
                "id": "19",
                "name": "CO2",
                "outlet": "19",
                "on": True,
                "stay_off_on_boot": False,
            },
            {
                "id": "20",
                "name": "Heater",
                "outlet": "20",
                "on": False,
                "stay_off_on_boot": False,
            },
            {
                "id": "21",
                "name": "Cooler",
                "outlet": "21",
                "on": False,
                "stay_off_on_boot": False,
            },
        ],
    )

    mock.get(f"{url}/api/tcs").respond(
        200, json=[{"id": "1", "name": "Temp", "fahrenheit": False}]
    )

    mock.get(f"{url}/api/tcs/1/current_reading").respond(
        200, json={"temperature": "25.0"}
    )

    mock.get(f"{url}/api/inlets").respond(200, json={})
