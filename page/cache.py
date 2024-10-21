from urllib.parse import urlparse

import boto3
from botocore.config import Config

from util import config, get_logger

logger = get_logger(__name__)


def _extract_host_and_path(url):
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    path = parsed_url.path
    query = parsed_url.query
    query_sep = '?' if query else ''
    return hostname, path + query_sep + query


def store_page(html_data: str, url: str, device: str) -> str:
    s3_endpoint = config.get('s3_endpoint')
    s3 = boto3.client(
        's3',
        aws_access_key_id=config.get('s3_access_key'),
        aws_secret_access_key=config.get('s3_secret_key'),
        endpoint_url=f'https://{s3_endpoint}',
        config=Config(signature_version='s3v4')
    )

    bucket_name = config.get('s3_bucket_name')
    hostname, path = _extract_host_and_path(url)
    object_name = hostname + '/' + device + path

    logger.debug(
        'store_page: storing %s in %s, bucket %s',
        object_name,
        s3_endpoint,
        bucket_name
    )
    try:
        # Upload the HTML data to the DigitalOcean Space bucket
        s3.put_object(
            Bucket=bucket_name,
            Key=object_name,
            Body=html_data,
            ContentType='text/html',
            ACL='public-read'
        )
        obj_path = object_name.replace(' ', '%20')
        url = f'https://{bucket_name}.{s3_endpoint}/{obj_path}'
        logger.debug(
            'store_page: s3 object direct URL: %s',
            url
        )
        return url
    except Exception as e:
        logger.exception('store_page: error storing %s: %s', object_name, e)
