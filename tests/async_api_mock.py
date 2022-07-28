from http.cookiejar import Cookie
import pytest
import httpx
import respx

REEF_MOCK_URL = "http://192.168.1.123"
REEF_MOCK_USER = "reef_pi"
REEF_MOCK_PASSWORD = "reef_password"

def mock_signin(mock, url = REEF_MOCK_URL):
    mock.post(f'{url}/auth/signin').respond(200, headers={'set-cookie':'auth=token'})

def mock_capabilities(mock, ph=True, url = REEF_MOCK_URL):
    mock.get(f'{url}/api/capabilities', cookies={"auth": "token"}).respond(200, json={
        'dev_mode': False,
        'dashboard': False,
        'health_check': False,
        'equipment': True,
        'timers': False,
        'lighting': False,
        'temperature': True,
        'ato': True,
        'camera': False,
        'doser': True,
        'ph': ph,
        'macro': False,
        'configuration': False,
        'journal': False})

def mock_phprobes(mock, url = REEF_MOCK_URL):
        mock.get(f'{url}/api/phprobes').respond(200, json=[
            {"id": "6",
             "name": "pH",
             "enable": True,
             "period": 15,
             "analog_input": "1",
             "control": True,
             "notify": {
                 "enable": True,
                 "min": 7.5,
                 "max": 8.6},
             "upper_eq": "10",
             "downer_eq": "9",
             "min": 8.1,
             "max": 8.25,
             "hysteresis": 0.1,
             "is_macro": False,
             "one_shot": False,
             "chart": {
                 "ymin": 0,
                 "ymax": 0,
                 "color": "", "unit": ""}},
            {"id": "7",
             "name": "pH No current",
             "enable": True,
            }, 
            {"id": "8",
             "name": "pH No history",
             "enable": True,
            }])

def mock_ph6(mock, url = REEF_MOCK_URL):
    mock.get(f'{url}/api/phprobes/6/readings').respond(200, json={
            "current":[
                {"value":8.191549295774648,"up":0,"down":15,"time":"Jun-08-02:07, 2021"},
                {"value":8.24507042253521,"up":0,"down":15,"time":"Jun-08-02:08, 2021"},
                {"value":8.185915492957747,"up":0,"down":15,"time":"Jun-08-02:08, 2021"},
                {"value":8.225352112676056,"up":0,"down":15,"time":"Jun-08-02:08, 2021"},
                {"value":8.216901408450704,"up":0,"down":15,"time":"Jun-08-02:08, 2021"},
                {"value":8.216901408450704,"up":0,"down":15,"time":"Jun-08-02:09, 2021"},
                {"value":8.264788732394367,"up":0,"down":15,"time":"Jun-08-02:09, 2021"},
                {"value":8.23943661971831,"up":0,"down":15,"time":"Jun-08-02:09, 2021"},
                {"value":8.230985915492958,"up":0,"down":15,"time":"Jun-08-02:09, 2021"},
                {"value":8.191549295774648,"up":0,"down":15,"time":"Jun-08-02:10, 2021"},
                {"value":8.228169014084507,"up":0,"down":15,"time":"Jun-08-02:10, 2021"},
                {"value":8.256338028169015,"up":0,"down":15,"time":"Jun-08-02:10, 2021"},
                {"value":8.24507042253521,"up":0,"down":15,"time":"Jun-08-02:10, 2021"},
                {"value":8.177464788732394,"up":0,"down":15,"time":"Jun-08-02:11, 2021"},
                {"value":8.177464788732394,"up":0,"down":15,"time":"Jun-08-02:11, 2021"},
                {"value":8.261971830985916,"up":0,"down":15,"time":"Jun-08-02:11, 2021"},
                {"value":8.270422535211267,"up":0,"down":15,"time":"Jun-08-02:11, 2021"},
                {"value":8.273239436619718,"up":0,"down":15,"time":"Jun-08-02:12, 2021"},
                {"value":8.236619718309859,"up":0,"down":15,"time":"Jun-08-02:12, 2021"},
                {"value":8.194366197183099,"up":0,"down":15,"time":"Jun-08-02:12, 2021"},
                {"value":8.194366197183099,"up":0,"down":15,"time":"Jun-08-02:12, 2021"},
                {"value":8.253521126760564,"up":0,"down":15,"time":"Jun-08-02:13, 2021"},
                {"value":8.270422535211267,"up":0,"down":15,"time":"Jun-08-02:13, 2021"},
                {"value":8.194366197183099,"up":0,"down":15,"time":"Jun-08-02:13, 2021"}],
            "historical":[
                {"value":8.14,"up":3000,"down":0,"time":"Mar-07-13:00, 2021"},
                {"value":8.15,"up":3420,"down":0,"time":"Mar-07-14:00, 2021"},
                {"value":8.14,"up":2760,"down":0,"time":"Mar-07-15:00, 2021"},
                {"value":8.17,"up":165,"down":135,"time":"Mar-07-16:00, 2021"},
                {"value":8.21,"up":0,"down":2085,"time":"Mar-07-17:00, 2021"},
                {"value":8.24,"up":0,"down":3555,"time":"Mar-07-18:00, 2021"},
                {"value":8.26,"up":0,"down":3600,"time":"Mar-07-19:00, 2021"},
                {"value":8.26,"up":0,"down":3600,"time":"Mar-07-20:00, 2021"},
                {"value":8.26,"up":0,"down":3600,"time":"Mar-07-21:00, 2021"},
                {"value":8.24,"up":0,"down":3600,"time":"Mar-07-22:00, 2021"},
                {"value":8.22,"up":0,"down":3600,"time":"Mar-07-23:00, 2021"}]
        })

def mock_ph78(mock, url = REEF_MOCK_URL):
    mock.get(f'{url}/api/phprobes/7/readings').respond(200, json={
            "historical":[
                {"value":4.0,"up":0,"down":15,"time":"Jun-08-02:07, 2021"},
                {"value":5.1,"up":0,"down":15,"time":"Jun-08-02:08, 2021"}]})

    mock.get(f'{url}/api/phprobes/8/readings').respond(200, json={})

def mock_info(mock, url = REEF_MOCK_URL):
    mock.get(f'{url}/api/info').respond(200, json={
            'name': 'reef-pi',
            'ip': '192.168.1.123',
            'current_time': 'Sat Jun 12 22:05:32',
            'uptime': '1 week ago',
            'cpu_temperature': "39.0'C\n",
            'version': '4.1',
            'model': 'Raspberry Pi 2 Model B Rev 1.1\x00'})


def mock_atos(mock, url = REEF_MOCK_URL, empty_usage = False):
    mock.get(f'{url}/api/atos').respond(200, json = [
        {
            "id":"1",
            "is_macro":False,
            "inlet":"2",
            "pump":"1",
            "period":120,
            "control":True,
            "enable":True,
            "notify":{
                "enable":False,
                "max":0
                },
            "name":"Test ATO",
            "disable_on_alert":False,
            "one_shot":False}])

    if empty_usage:
        mock.get(f'{url}/api/atos/1/usage').respond(200, json = {})
    else:
        mock.get(f'{url}/api/atos/1/usage').respond(200, json = {"current":[{"pump":120,"time":"Jan-11-09:01, 2022"}, {"pump":0,"time":"Jan-12-09:01, 2022"}]})

def mock_all(mock, url = REEF_MOCK_URL, has_ph = True, has_ato_usage = True):
        mock_signin(mock)
        mock_capabilities(mock)
        mock_info(mock)
        mock_phprobes(mock)
        mock_ph6(mock)
        mock_ph78(mock)
        mock_atos(mock, empty_usage=not has_ato_usage)

        mock.get(f'{url}/api/doser/pumps').respond(200, json=[
            {"id": "1", "name": "Pump1 sched1", "jack": "1", "pin": 0, "regiment": {"enable": True, "schedule": 
                    {"day": "*","hour": "19","minute": "30","second": "0","week": "*","month": "*"},
                    "duration": 15,"speed": 20}},
            {"id": "2", "name": "Pump1 sched2", "jack": "1", "pin": 0, "regiment": {"enable": True, "schedule": 
                    {"day": "*","hour": "20","minute": "30","second": "0","week": "*","month": "*"},
                    "duration": 15,"speed": 20}},
            {"id": "3", "name": "Pump2 sched1", "jack": "2", "pin": 1, "regiment": {"enable": True, "schedule": 
                    {"day": "*","hour": "21","minute": "30","second": "0","week": "*","month": "*"},
                    "duration": 15,"speed": 20}},
            {"id": "4", "name": "Pump2 sched1", "jack": "2", "pin": 2, "regiment": {"enable": True, "schedule": 
                    {"day": "*","hour": "22","minute": "30","second": "0","week": "*","month": "*"},
                    "duration": 15,"speed": 20}},
            {"id": "5", "name": "No history", "jack": "3", "pin": 0, "regiment": {"enable": True, "schedule": 
                    {"day": "*","hour": "22","minute": "30","second": "0","week": "*","month": "*"},
                    "duration": 15,"speed": 20}}
        ])

        mock.get(f'{url}/api/doser/pumps/1/usage').respond(200, json= {
            "current": [
                {"pump":11,"time":"Aug-18-14:05, 2021"},
                {"pump":15,"time":"Aug-18-19:30, 2021"},
                {"pump":15,"time":"Aug-19-19:30, 2021"},
                {"pump":15,"time":"Aug-20-19:30, 2021"},
                {"pump":15,"time":"Aug-21-19:30, 2021"},
                {"pump":15,"time":"Aug-22-19:30, 2021"},
                {"pump":15,"time":"Aug-23-19:30, 2021"}],
            "historical": [
                {"pump":26,"time":"Aug-18-14:05, 2021"},
                {"pump":15,"time":"Aug-19-19:30, 2021"},
                {"pump":15,"time":"Aug-20-19:30, 2021"},
                {"pump":15,"time":"Aug-21-19:30, 2021"},
                {"pump":15,"time":"Aug-22-19:30, 2021"},
                {"pump":15,"time":"Aug-23-19:30, 2021"}]
        })

        mock.get(f'{url}/api/doser/pumps/2/usage').respond(200, json= {
            "current": [
                {"pump":11,"time":"Aug-18-14:05, 2021"},
                {"pump":15,"time":"Aug-18-19:30, 2021"},
                {"pump":15,"time":"Aug-19-19:30, 2021"},
                {"pump":15,"time":"Aug-20-19:30, 2021"},
                {"pump":15,"time":"Aug-21-19:30, 2021"},
                {"pump":15,"time":"Aug-22-19:30, 2021"},
                {"pump":15,"time":"Aug-23-20:30, 2021"}],
            "historical": [
                {"pump":26,"time":"Aug-18-14:05, 2021"},
                {"pump":15,"time":"Aug-19-19:30, 2021"},
                {"pump":15,"time":"Aug-20-19:30, 2021"},
                {"pump":15,"time":"Aug-21-19:30, 2021"},
                {"pump":15,"time":"Aug-22-21:30, 2021"}]
        })

        mock.get(f'{url}/api/doser/pumps/3/usage').respond(200, json= {
            "current": [
                {"pump":11,"time":"Aug-18-14:05, 2021"},
                {"pump":15,"time":"Aug-18-19:30, 2021"},
                {"pump":15,"time":"Aug-19-19:30, 2021"},
                {"pump":15,"time":"Aug-20-19:30, 2021"},
                {"pump":15,"time":"Aug-21-19:30, 2021"},
                {"pump":15,"time":"Aug-23-21:30, 2021"}],
            "historical": [
                {"pump":26,"time":"Aug-18-14:05, 2021"},
                {"pump":15,"time":"Aug-19-19:30, 2021"},
                {"pump":15,"time":"Aug-20-19:30, 2021"},
                {"pump":15,"time":"Aug-21-19:30, 2021"},
                {"pump":15,"time":"Aug-22-19:30, 2021"},
                {"pump":15,"time":"Aug-23-22:30, 2021"}]
        })

        mock.get(f'{url}/api/doser/pumps/4/usage').respond(200, json= {
            "historical": [
                {"pump":26,"time":"Aug-18-14:05, 2021"},
                {"pump":15,"time":"Aug-19-19:30, 2021"},
                {"pump":15,"time":"Aug-20-19:30, 2021"},
                {"pump":15,"time":"Aug-21-19:30, 2021"},
                {"pump":15,"time":"Aug-22-19:30, 2021"},
                {"pump":15,"time":"Aug-23-19:30, 2021"}]
        })

        mock.get(f'{url}/api/doser/pumps/5/usage').respond(200, json= {
        })

        mock.get(f'{url}/api/equipment').respond(200, json = 
            [
                {"id": "1", "name": "Old light", "outlet": "1", "on": True, "stay_off_on_boot": False}, 
                {"id": "17", "name": "Led light 1", "outlet": "17", "on": False, "stay_off_on_boot": False}, 
                {"id": "18", "name": "Led light 2", "outlet": "18", "on": True, "stay_off_on_boot": False}, 
                {"id": "19", "name": "CO2", "outlet": "19", "on": True, "stay_off_on_boot": False}, 
                {"id": "20", "name": "Heater", "outlet": "20", "on": False, "stay_off_on_boot": False}, 
                {"id": "21", "name": "Cooler", "outlet": "21", "on": False, "stay_off_on_boot": False}]
        )

        mock.get(f'{url}/api/tcs').respond(200, json = [{"id": "1", "name": "Temp", "fahrenheit": False}])

        mock.get(f'{url}/api/tcs/1/current_reading').respond(200, json={'temperature': '25.0'})

        mock.get(f'{url}/api/inlets').respond(200, json={})
