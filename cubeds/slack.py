from slackclient import SlackClient
import cubeds.pylogger


def write_to_slack(message, config):
    logger = cubeds.pylogger.get_logger(__name__)
    key = config.config['ingest_stats'][config.yaml_key]['slack']['key']
    slack_client = SlackClient(key)

    slack_client.api_call(
        "chat.postMessage",
        channel=config.config['ingest_stats'][config.yaml_key]['slack']['channel'],
        text=message
    )
    logger.info("Wrote statistic info to Slack workspace.")

