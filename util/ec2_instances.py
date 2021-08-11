import batch
import pprint as pp


class EC2InstanceData():

    def get_data(self, profile):
        print('Get ec2 instance data for AWS profile:', profile)
        try:
            data = batch.get_cached_data('ec2', profile, 'details')
        except Exception as e:
            print(str(e))
            raise Exception(
                'You may need to rerun script cache_ec2_instance_data.py for this project'
            )
        return data
        
        
   
