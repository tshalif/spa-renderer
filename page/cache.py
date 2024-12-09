import re
from typing import Tuple, Union
from urllib.parse import parse_qs, urlencode, urlparse

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from util import config, get_logger

logger = get_logger(__name__)


def _ignore_query_params(query) -> str:
    parsed_query = parse_qs(query)
    ignore_params = [
        *config.get('s3_ignore_query_params'),
        *config.get('s3_ignore_query_params_extra')
    ]
    keys = list(parsed_query.keys())
    for i in ignore_params:
        ignore_pattern = re.compile(f'^{i}$')
        for k in keys:
            if ignore_pattern.match(k):
                del parsed_query[k]
                break
                pass
            pass
        pass
    return urlencode(parsed_query, doseq=True)


def _extract_host_and_path(url):
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    path = parsed_url.path
    query = _ignore_query_params(parsed_url.query)
    query_sep = '?' if query else ''
    return hostname, path + query_sep + query


def _s3_config(device, url) -> Tuple[str, str, BaseClient, str, str]:
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
    if path and path[-1] == '/':
        path = path[0:-1]  # strip trailing '/' from S3 storage key
    pass
    object_name = hostname + '/' + device.replace(' ', '').lower() + path
    logger.debug(
        '_s3_config: object=%s, endpoint=%s, bucket=%s',
        object_name,
        s3_endpoint,
        bucket_name
    )
    obj_path = object_name.replace(' ', '%20')
    s3_url = f'https://{bucket_name}.{s3_endpoint}/{obj_path}'
    return bucket_name, object_name, s3, s3_endpoint, s3_url


def get_page(device: str, url: str) -> Tuple[Union[str, None], str]:
    bucket_name, object_name, s3, _, s3_url = _s3_config(device, url)
    try:
        obj = s3.get_object(
            Bucket=bucket_name,
            Key=object_name
        )

    except s3.exceptions.NoSuchKey:
        logger.debug('get_page: object %s not found in S3 cache', object_name)
        return None, s3_url
    except Exception as e:
        logger.exception('get_page: error retrieving %s: %s', object_name, e)
        return None, s3_url
    else:
        logger.debug(
            'get_page: object %s retrieved from S3 cache',
            object_name
        )
        return obj['Body'].read().decode('utf-8'), s3_url


def store_page(html_data: str, url: str, device: str) -> str:
    bucket_name, object_name, s3, s3_endpoint, s3_url = _s3_config(device, url)
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
            s3_url
        )
        return s3_url
    except Exception as e:
        logger.exception('store_page: error storing %s: %s', object_name, e)
        return ''
