import batch
import pprint as pp


class ConfigData():

    def get_data(self, profile):
        print('Get config data for AWS profile:', profile)
        try:
            data = batch.get_cached_data('config', profile, 'detail')
        except Exception as e:
            print(str(e))
            raise Exception(
                'You may need to rerun script cache_aws_config_data.py for this project'
            )
        return data
        
        
   
