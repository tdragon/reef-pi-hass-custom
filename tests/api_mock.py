import pytest
import requests
import requests_mock

REEF_MOCK_URL = "http://192.168.1.123"
REEF_MOCK_USER = "reef_pi"
REEF_MOCK_PASSWORD = "reef_password"

class ApiMock:
    def __init__(self, requests_mock, url = REEF_MOCK_URL):
        self.requests_mock = requests_mock
        self.url = url
        self.requests_mock.post(f'{self.url}/auth/signin', cookies={'auth': 'token'}, status_code=200)
        self.requests_mock.get(f'{self.url}/api/capabilities', json={
            'dev_mode': False,
            'dashboard': True,
            'health_check': True,
            'equipment': True,
            'timers': True,
            'lighting': False,
            'temperature': True,
            'ato': False,
            'camera': False,
            'doser': False,
            'ph': True,
            'macro': False,
            'configuration': True,
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
                 "color": "", "unit": ""}}])

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
        