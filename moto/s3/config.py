from moto.core.exceptions import InvalidNextTokenException
from moto.core.models import ConfigQueryModel
from moto.s3 import s3_backends


class S3ConfigQuery(ConfigQueryModel):

    def list_config_service_resources(self, resource_ids, resource_name, limit, next_token, backend_region=None, resource_region=None):
        # S3 need not care about "backend_region" as S3 is global. The resource_region only matters for aggregated queries as you can
        # filter on bucket regions for them. For other resource types, you would need to iterate appropriately for the backend_region.

        # Resource IDs are the same as S3 bucket names
        # For aggregation -- did we get both a resource ID and a resource name?
        if resource_ids and resource_name:
            # If the values are different, then return an empty list:
            if resource_name not in resource_ids:
                return [], None

        # If no filter was passed in for resource names/ids then return them all:
        if not resource_ids and not resource_name:
            bucket_list = list(self.backends['global'].buckets.keys())

        else:
            # Match the resource name / ID:
            bucket_list = []
            filter_buckets = [resource_name] if resource_name else resource_ids

            for bucket in self.backends['global'].buckets.keys():
                if bucket in filter_buckets:
                    bucket_list.append(bucket)

        # If a resource_region was supplied (aggregated only), then filter on bucket region too:
        if resource_region:
            region_buckets = []

            for bucket in bucket_list:
                if self.backends['global'].buckets[bucket].region_name == resource_region:
                    region_buckets.append(bucket)

            bucket_list = region_buckets

        if not bucket_list:
            return [], None

        # Pagination logic:
        sorted_buckets = sorted(bucket_list)
        new_token = None

        # Get the start:
        if not next_token:
            start = 0
        else:
            # Tokens for this moto feature is just the bucket name:
            # For OTHER non-global resource types, it's the region concatenated with the resource ID.
            if next_token not in sorted_buckets:
                raise InvalidNextTokenException()

            start = sorted_buckets.index(next_token)

        # Get the list of items to collect:
        bucket_list = sorted_buckets[start:(start + limit)]

        if len(sorted_buckets) > (start + limit):
            new_token = sorted_buckets[start + limit]

        return [{'type': 'AWS::S3::Bucket', 'id': bucket, 'name': bucket, 'region': self.backends['global'].buckets[bucket].region_name}
                for bucket in bucket_list], new_token


s3_config_query = S3ConfigQuery(s3_backends)
