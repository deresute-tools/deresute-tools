import requests

_headers = {
    'X-Unity-Version': '2018.3.8f1',
    'Accept-Encoding': 'gzip',
}


def get_resources(data_type, resource_hash):
    return requests.get(
        "https://asset-starlight-stage.akamaized.net/dl/resources/{}/{}/{}".format(data_type, resource_hash[:2],
                                                                                   resource_hash), headers=_headers)


def get_manifests():
    from src.network import kirara_query
    truth_version = kirara_query.get_truth_version()
    return requests.get(
        "https://asset-starlight-stage.akamaized.net/dl/{}/manifests/Android_AHigh_SHigh".format(truth_version),
        headers=_headers)


def get_db(resource_hash):
    return get_resources('Generic', resource_hash)
