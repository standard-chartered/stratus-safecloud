import batch
import pprint as pp


class SecurityData():

    def get_data(self, profile):
        print('Get security data for AWS profile:', profile)
        try:
            data = batch.get_cached_data('security', profile, 'detail')
        except Exception as e:
            print(str(e))
            raise Exception(
                'You may need to rerun script cache_aws_security_daya.py for this project'
            )
        return data
        
    def get_scores(self, profile):
        print('Get security score for AWS profile:', profile)
        try:
            data = batch.get_cached_data('security', profile, 'score')
        except Exception as e:
            print(str(e))
            raise Exception(
                'You may need to rerun script cache_aws_security_daya.py for this project'
            )
        return data
        
   
