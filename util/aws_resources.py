import batch
import pprint as pp


class ResourceData():

    def get_data(self, profile):
        print('Get resource data for AWS profile:', profile)
        try:
            data = batch.get_cached_data('infra', profile, 'infra')
        except Exception as e:
            print(str(e))
            raise Exception(
                'You may need to rerun script cache_aws_infra.py for this profile'
            )
        return data
                
   
