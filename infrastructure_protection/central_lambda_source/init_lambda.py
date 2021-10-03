import os
import boto3
import json
import datetime
from aws_gameday_quests.gdQuestsApi import GameDayQuestsApiClient

# Standard AWS GameDay Quests Environment Variables
QUEST_ID = os.environ['QUEST_ID']
QUEST_API_BASE = os.environ['QUEST_API_BASE']
QUEST_API_TOKEN = os.environ['QUEST_API_TOKEN']
GAMEDAY_REGION = os.environ['GAMEDAY_REGION']

# Icebreaker Quest Environment Variables
QUEST_TEAM_STATUS_TABLE = os.environ['QUEST_TEAM_STATUS_TABLE']
dynamodb = boto3.resource('dynamodb')
icebreaker_status_table = dynamodb.Table(QUEST_TEAM_STATUS_TABLE)


def lambda_handler(event, context):
	print(f"Icebreaker Quest INIT_LAMBDA invocation, event={json.dumps(event, default=str)}, context={str(context)}")

	# Instantiate the Quest API Client.
	quests_api_client = GameDayQuestsApiClient(QUEST_API_BASE, QUEST_API_TOKEN)

	event_status = quests_api_client.get_event_status()
	if event_status['status'] != 'IN_PROGRESS':
		print(f"Event Status: {event_status}, aborting INIT_LAMBDA")
		return

	# Get the team_id from the previous event sent by the Lambda that called this function (sns_lambda)
	team_id = event['team_id']

	team_data = quests_api_client.get_team(team_id=team_id)

	parameter_value = retrieve_parameter_value(quests_api_client, team_data, "ERROR_NO_VALUE!")

	# Populate the QUEST_TEAM_STATUS_TABLE for this team
	dynamo_put_response = icebreaker_status_table.put_item(
		Item={
			'team-id': str(team_id),
			'quest-start-time': int(datetime.datetime.now().timestamp()),  # We can live without milliseconds
			'success-returned': False,
			'correct-role-input': False,
			'parameter-value': parameter_value,
			'correct-parameter': False,
			'score-weight-progress': 0
		}
	)
	print(f"Created team {team_id} in {QUEST_TEAM_STATUS_TABLE}. Response: {json.dumps(dynamo_put_response, default=str)}")

	# Post the initial challenge to the team via an output, we'll overwrite this later when they've done it
	quests_api_client.post_output(
		team_id=team_id,
		quest_id=QUEST_ID,
		key='call_to_action_1',
		label='Welcome',
		value="Sometimes here at Unicorn.Rentals, it is easier to perform some tasks with the AWS CLI. " +
		"Try launching AWS CloudShell from the AWS Console Service menu and experimenting with some commands!",
		dashboard_index=1,
		markdown=True,
	)
	if parameter_value == "ERROR_NO_VALUE!":
		raise Exception(f"INIT_LAMBDA for team {team_id} was unable to retrieve the parameter value!")


# AssumeRole into the Team account's OpsRole, and check the Enable CloudFormation Stack for this Quest
# Not trusting the current parameter value in case the team changes it for some reason.
def retrieve_parameter_value(quests_api_client, team_data, error_value="ERROR_NO_VALUE!"):
	print(f"Assuming role {team_data['ops-role-arn']} for team {team_data['team-id']}")
	xa_session = quests_api_client.assume_team_ops_role(team_data['team-id'])
	quest_enable_stack_name = f"gdQuests-{QUEST_ID}-Enable"
	print(f"Getting outputs for {quest_enable_stack_name}")

	cfn_client = xa_session.client("cloudformation")
	cfn_response = cfn_client.describe_stacks(StackName=quest_enable_stack_name)
	print(f"Stack outputs: {json.dumps(cfn_response, default=str)}")

	for output in cfn_response['Stacks'][0]['Outputs']:
		if output['OutputKey'] == "IcebreakerParameterValue":
			parameter_value = output['OutputValue']
			print(f"Found parameter_value {parameter_value}")
			return parameter_value
	# if we got here, there was a problem with the stack or the code or the output
	# Return an error value and we'll throw an exception later in the process for
	# Better Event Operator experience
	return error_value

