from subprocess import Popen
import time
import os
import signal
import psutil
from random import randint

import unittest
import requests
import runpy


rand = randint(0,pow(10,12))
ds_name = f'hr_ds_{rand}'
pred_name =  f'hr_predictor_{rand}'
root = 'http://localhost:47334'


class HTTPTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sp = Popen(['python3', '-m', 'mindsdb', '--api', 'http'], close_fds=True)

        for i in range(20):
            try:
                res = requests.get(f'{root}/util/ping')
                if res.status_code != 200:
                    raise Exception('')
            except Exception:
                time.sleep(1)
                if i == 19:
                    raise Exception("Can't connect !")

    @classmethod
    def tearDownClass(cls):
        try:
            conns = psutil.net_connections()
            pid = [x.pid for x in conns if x.status == 'LISTEN' and x.laddr[1] == 47334 and x.pid is not None]
            if len(pid) > 0:
                os.kill(pid[0], 9)
            cls.sp.kill()
        except Exception:
            pass

    def test_1_config(self):
        res = requests.get(f'{root}/config/integrations')
        assert res.status_code == 200
        integration_names = res.json()
        assert set(integration_names['integrations']) == set(['default_mariadb', 'default_clickhouse'])

        test_integration_data = {'enabled': False, 'host': 'test', 'type': 'clickhouse'}
        res = requests.put(f'{root}/config/integrations/test_integration', json={'params': test_integration_data})
        assert res.status_code == 200

        res = requests.get(f'{root}/config/integrations/test_integration')
        assert res.status_code == 200
        test_integration = res.json()
        assert len(test_integration) == 3

        res = requests.delete(f'{root}/config/integrations/test_integration')
        assert res.status_code == 200

        res = requests.get(f'{root}/config/integrations/test_integration')
        assert res.status_code != 200

        for k in test_integration_data:
            assert test_integration[k] == test_integration_data[k]

        for name in ['default_mariadb', 'default_clickhouse']:
            # Get the original
            res = requests.get(f'{root}/config/integrations/{name}')
            assert res.status_code == 200

            integration = res.json()
            for k in ['enabled','host','port','password','type','user']:
                assert k in integration
                assert integration[k] is not None

            # Modify it
            res = requests.post(f'{root}/config/integrations/{name}', json={'params':{'password':'test'}})

            res = requests.get(f'{root}/config/integrations/{name}')
            assert res.status_code == 200
            modified_integration = res.json()
            assert modified_integration['password'] == 'test'
            for k in integration:
                if k != 'password':
                    assert modified_integration[k] == integration[k]

            # Put the original values back in
            res = requests.post(f'{root}/config/integrations/{name}', json={'params':integration})
            res = requests.get(f'{root}/config/integrations/{name}')
            assert res.status_code == 200
            modified_integration = res.json()
            for k in integration:
                assert modified_integration[k] == integration[k]

    def test_2_put_ds(self):
        # PUT datasource
        params = {
            'name': ds_name,
            'source_type': 'url',
            'source': 'https://raw.githubusercontent.com/mindsdb/mindsdb-examples/master/benchmarks/home_rentals/dataset/train.csv'
        }
        url = f'{root}/datasources/{ds_name}'
        res = requests.put(url, json=params)
        assert res.status_code == 200

    def test_3_analyze(self):
        response = requests.get(f'{root}/datasources/{ds_name}/analyze')
        assert response.status_code == 200

    def test_3_put_predictor(self):
        # PUT predictor
        params = {
            'data_source_name': ds_name,
            'to_predict': 'rental_price',
            'kwargs': {
                'stop_training_in_x_seconds': 5,
                'join_learn_process': True
            }
        }
        url = f'{root}/predictors/{pred_name}'
        res = requests.put(url, json=params)
        assert res.status_code == 200

        # POST predictions
        params = {
            'when': {'sqft':500}
        }
        url = f'{root}/predictors/{pred_name}/predict'
        res = requests.post(url, json=params)
        assert isinstance(res.json()[0]['rental_price']['predicted_value'],float)
        assert res.status_code == 200

    def test_4_datasources(self):
        """
        Call list datasources endpoint
        THEN check the response is success
        """
        response = requests.get(f'{root}/datasources/')
        assert response.status_code == 200

    def test_5_datasource_not_found(self):
        """
        Call unexisting datasource
        then check the response is NOT FOUND
        """
        response = requests.get(f'{root}/datasource/dummy_source')
        assert response.status_code == 404

    def test_6_ping(self):
        """
        Call utilities ping endpoint
        THEN check the response is success
        """
        response = requests.get(f'{root}/util/ping')
        assert response.status_code == 200

    def test_7_predictors(self):
        """
        Call list predictors endpoint
        THEN check the response is success
        """
        response = requests.get(f'{root}/predictors/')
        assert response.status_code == 200

    def test_8_predictor_not_found(self):
        """
        Call unexisting predictor
        then check the response is NOT FOUND
        """
        response = requests.get(f'{root}/predictors/dummy_predictor')
        assert response.status_code == 404

if __name__ == '__main__':
    unittest.main(failfast=True)
