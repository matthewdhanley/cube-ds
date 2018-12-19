from slackclient import SlackClient
import config


LOGGER = config.pylogger.get_logger(__name__)


def write_to_slack(message):
    key = config.CONFIG_INFO['SLACK_CONFIG']['BOT_KEY']
    slack_client = SlackClient(key)

    slack_client.api_call(
        "chat.postMessage",
        channel=config.CONFIG_INFO['SLACK_CONFIG']['CHANNEL'],
        text=message
    )
    LOGGER.info("Wrote statistic info to Slack workspace.")
