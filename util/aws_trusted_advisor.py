import batch
import pprint as pp


class TrustedAdvisorData():

    def get_data(self, profile):
        print('Get trusted advisor data for AWS profile:', profile)
        try:
            data = batch.get_cached_data('trusted-advisor', profile, 'details')
        except Exception as e:
            print(str(e))
            raise Exception(
                'You may need to rerun script cache_aws_trusted_advisor_data.py for this project'
            )
        return data
        
    def get_results(self, profile):
        print('Get trusted advisor results for AWS profile:', profile)
        try:
            data = batch.get_cached_data('trusted-advisor', profile, 'results')
        except Exception as e:
            print(str(e))
            raise Exception(
                'You may need to rerun script cache_aws_trusted_advisor_data.py for this project'
            )
        return data
        
   
