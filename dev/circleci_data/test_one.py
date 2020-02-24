import os
import random
import yaml

from indi_aws import fetch_creds
from sys import argv

# bucket = fetch_creds.return_bucket(None, 'fcp-indi')

def getPrefix(url):
    """
    Function to get an S3 prefix from an S3 url

    :param url: str
    :return: str
    """
    return(url.split('/',3)[-1].strip('/'))


def expand_possibilitities(d):
    """
    Combines possibilities from dictionary into a flat list

    :param d: dict:
        site: {
            s3: url,
            sessions: list,
            subjects: list
        }
    :return: list of tuples (url, subject, session)
    """
    return([
        (
            d[site]['s3'],
            int(subject) if str.isnumeric(subject) else subject,
            int(session) if str.isnumeric(session) else session
        ) for site in d
        for subject in d[site]['subjects']
        for session in d[site]['sessions'] if (
            subject in d[site]['subjects'] and
            session in d[site]['sessions']
        )
    ])


def main(test_to_run):

    with open(
        os.path.join(os.path.dirname(__file__), 'test_data.yml'),
        'r'
    ) as f:
        # `test_subject` will be a tuple of (prefix, subject, session)
        test_subject = random.choice(
            expand_possibilitities(yaml.load(f, Loader=yaml.BaseLoader))
        )

    # for obj in bucket.objects.filter(Prefix=getPrefix(url)):
    #     print(obj.key)

    if isinstance(test_subject[1], int):
        test_to_run = f"{test_to_run} --participant_ndx {test_subject[1]}"
    else:
        test_to_run = (
            f"{test_to_run} --participant_label {test_subject[1].strip('sub-')}"
        )
    print(test_to_run)
    return(test_to_run)


def run():
    main(argv)


if __name__ == "__main__":
    run()
