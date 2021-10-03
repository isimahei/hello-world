import boto3
import json
import os
from aws_gameday_quests.gdQuestsApi import GameDayQuestsApiClient

# Standard AWS GameDay Quests Environment Variables
QUEST_ID = os.environ['QUEST_ID']
QUEST_API_BASE = os.environ['QUEST_API_BASE']
QUEST_API_TOKEN = os.environ['QUEST_API_TOKEN']
GAMEDAY_REGION = os.environ['GAMEDAY_REGION']

# Icebreaker Quest Environment Variables
EVENT_RULE_CRON = os.environ['EVENT_RULE_CRON']
QUEST_TEAM_STATUS_TABLE = os.environ['QUEST_TEAM_STATUS_TABLE']
INIT_LAMBDA = os.environ['INIT_LAMBDA']
UPDATE_LAMBDA = os.environ['UPDATE_LAMBDA']

lambda_client = boto3.client('lambda')
events_client = boto3.client('events')


def lambda_handler(event, context):
    print(f"Icebreaker sns_lambda invocation, event:{json.dumps(event, default=str)}, context: {str(context)}")

    # Instantiate the Quest API Client.
    quests_api_client = GameDayQuestsApiClient(QUEST_API_BASE, QUEST_API_TOKEN)
    # Check if event is running
    event_status = quests_api_client.get_event_status()
    if event_status['status'] != 'IN_PROGRESS':
        print(f"Event Status: {event_status}, aborting SNS_LAMBDA")
        return

    # Pulling the message portion out of the SNS message.
    # Always a single message: https://aws.amazon.com/sns/faqs/#Reliability
    # This is a json object pushed by the QDK SNS topic whenever something of note happens
    message = event['Records'][0]['Sns']['Message']
    sns_values = json.loads(message)
    team_id = sns_values['team-id']
    quest_id = sns_values['quest-id']

    # IMPORTANT! Filter on Quest ID to ensure relevancy to this quest (there are others in the event)
    if quest_id != QUEST_ID:
        print(f"Message for Quest: {quest_id}, this Quest is {QUEST_ID}, disregarding")
        return

    sns_type = event['Records'][0]['Sns']['MessageAttributes']['event']['Value']

    print(f"Icebreaker SNS Message for team {team_id}: {message}")

    # Switch on SNS event type and delegate to the appropriate lambda
    # If quest was enabled, initialize quest outputs
    if sns_type == 'gdQuests:QUEST_IN_PROGRESS':
        print(f"Icebreaker Quest event: QUEST_IN_PROGRESS for team {team_id}... Invoking {INIT_LAMBDA}")

        # providing payload for init_lambda
        init_params = {'team_id': team_id}
        lambda_invoke_response = lambda_client.invoke(
            FunctionName=INIT_LAMBDA,
            InvocationType='Event',
            Payload=json.dumps(init_params, default=str)
        )
        print(lambda_invoke_response)

    elif sns_type == 'gdQuests:QUEST_STOPPED':
        print(f"Icebreaker Quest event: QUEST_STOPPED for team {team_id}... " +
              f"No action to take, CRON_LAMBDA will filter")

    elif sns_type == 'gdQuests:INPUT_UPDATED':
        key = sns_values['key']
        value = sns_values['value']
        print(f"Icebreaker Quest event: INPUT_UPDATED for team {team_id}, ({key}={value}), " +
              f"triggering {UPDATE_LAMBDA}...")

        # providing payload for update_lambda  
        update_params = {
            'team_id': team_id,
            'key': key,
            'value': value
        }
        lambda_invoke_response = lambda_client.invoke(
            FunctionName=UPDATE_LAMBDA,
            InvocationType='Event',
            Payload=json.dumps(update_params, default=str))
        print(lambda_invoke_response)

    elif sns_type == 'gdQuests:QUEST_DEPLOYING':
        print(f"Icebreaker Quest SNS Lambda processing QUEST_DEPLOYING message, " +
              f"ensuring EventBridge Cron Rule Enabled.")

        # TODO Fix this in the immersion deck

        # EventBridge cron should be enabled by default in the CFN template, but confirm at initialization just in case
        response = events_client.enable_rule(Name=EVENT_RULE_CRON)
        print("ENABLED " + EVENT_RULE_CRON, response)
    elif sns_type == 'gdQuests:QUEST_TERMINATED':
        print(f"Icebreaker Quest SNS Lambda processing QUEST_TERMINATED message, disabling EventBridge Cron Rule.")

        response = events_client.enable_rule(Name=EVENT_RULE_CRON)
        print("DISABLED " + EVENT_RULE_CRON, response)
    else:
        # Unknown or unhandled message type. This is fine, just log.
        print(f"Icebreaker Quest, unknown SNS message: {sns_values}")
