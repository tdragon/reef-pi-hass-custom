import pytest
import requests
import requests_mock

REEF_MOCK_URL = "http://192.168.1.123"
REEF_MOCK_USER = "reef_pi"
REEF_MOCK_PASSWORD = "reef_password"

class ApiMock:
    def __init__(self, requests_mock, url = REEF_MOCK_URL, has_ph = True):
        self.requests_mock = requests_mock
        self.url = url
        self.requests_mock.post(f'{self.url}/auth/signin', cookies={'auth': 'token'}, status_code=200)

        self.requests_mock.get(f'{self.url}/api/info', json={
            'name': 'reef-pi',
            'ip': '192.168.1.123',
            'current_time': 'Sat Jun 12 22:05:32',
            'uptime': '1 week ago',
            'cpu_temperature': "39.0'C\n",
            'version': '4.1',
            'model': 'Raspberry Pi 2 Model B Rev 1.1\x00'})
            
        self.requests_mock.get(f'{self.url}/api/capabilities', json={
            'dev_mode': False,
            'dashboard': False,
            'health_check': False,
            'equipment': True,
            'timers': False,
            'lighting': False,
            'temperature': False,
            'ato': False,
            'camera': False,
            'doser': True,
            'ph': has_ph,
            'macro': False,
            'configuration': False,
            'journal': False})

        self.requests_mock.get(f'{self.url}/api/phprobes', json=[
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

        self.requests_mock.get(f'{self.url}/api/phprobes/unknown/readings', status_code=404)
        self.requests_mock.get(f'{self.url}/api/phprobes/6/readings', json={
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

        self.requests_mock.get(f'{self.url}/api/phprobes/7/readings', json={
            "historical":[
                {"value":4.0,"up":0,"down":15,"time":"Jun-08-02:07, 2021"},
                {"value":5.1,"up":0,"down":15,"time":"Jun-08-02:08, 2021"}]})

        self.requests_mock.get(f'{self.url}/api/phprobes/8/readings', json={})

        self.requests_mock.get(f'{self.url}/api/doser/pumps', json=[
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

        self.requests_mock.get(f'{self.url}/api/doser/pumps/1/usage', json= {
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

        self.requests_mock.get(f'{self.url}/api/doser/pumps/2/usage', json= {
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

        self.requests_mock.get(f'{self.url}/api/doser/pumps/3/usage', json= {
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

        self.requests_mock.get(f'{self.url}/api/doser/pumps/4/usage', json= {
            "historical": [
                {"pump":26,"time":"Aug-18-14:05, 2021"},
                {"pump":15,"time":"Aug-19-19:30, 2021"},
                {"pump":15,"time":"Aug-20-19:30, 2021"},
                {"pump":15,"time":"Aug-21-19:30, 2021"},
                {"pump":15,"time":"Aug-22-19:30, 2021"},
                {"pump":15,"time":"Aug-23-19:30, 2021"}]
        })

        self.requests_mock.get(f'{self.url}/api/doser/pumps/5/usage', json= {
        })

        self.requests_mock.get(f'{self.url}/api/equipment', json = 
            [
                {"id": "1", "name": "Old light", "outlet": "1", "on": True, "stay_off_on_boot": False}, 
                {"id": "17", "name": "Led light 1", "outlet": "17", "on": False, "stay_off_on_boot": False}, 
                {"id": "18", "name": "Led light 2", "outlet": "18", "on": True, "stay_off_on_boot": False}, 
                {"id": "19", "name": "CO2", "outlet": "19", "on": True, "stay_off_on_boot": False}, 
                {"id": "20", "name": "Heater", "outlet": "20", "on": False, "stay_off_on_boot": False}, 
                {"id": "21", "name": "Cooler", "outlet": "21", "on": False, "stay_off_on_boot": False}]
        )
