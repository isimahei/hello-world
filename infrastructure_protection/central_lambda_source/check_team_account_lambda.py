import os
import datetime
import boto3
import json
import requests
from aws_gameday_quests.gdQuestsApi import GameDayQuestsApiClient

# Standard AWS GameDay Quests Environment Variables
QUEST_ID = os.environ['QUEST_ID']
QUEST_API_BASE = os.environ['QUEST_API_BASE']
QUEST_API_TOKEN = os.environ['QUEST_API_TOKEN']
GAMEDAY_REGION = os.environ['GAMEDAY_REGION']

# Icebreaker Quest Environment Variables
QUEST_TEAM_STATUS_TABLE = os.environ['QUEST_TEAM_STATUS_TABLE']

dynamodb = boto3.resource('dynamodb')


# Expected event payload is the QuestsAPI entry for this team
def lambda_handler(event, context):
    print(f"check_team_account_lambda invocation, event:{json.dumps(event, default=str)}, context: {str(context)}")

    # Instantiate the Quest API Client.
    quests_api_client = GameDayQuestsApiClient(QUEST_API_BASE, QUEST_API_TOKEN)
    # Check if event is running
    event_status = quests_api_client.get_event_status()
    if event_status['status'] != 'IN_PROGRESS':
        print(f"Event Status: {event_status}, aborting CHECK_TEAM_ACCOUNT_LAMBDA")
        return

    icebreaker_status_table = dynamodb.Table(QUEST_TEAM_STATUS_TABLE)
    dynamodb_response = icebreaker_status_table.get_item(Key={'team-id': event['team-id']})
    print(f"Retrieved Icebreaker team state for team {event['team-id']}: {json.dumps(dynamodb_response, default=str)}")
    team_data = dynamodb_response['Item']
    # Check init_lambda for the format

    # Establish decision tree branching
    check_for_shell = not team_data['cloudshell-launched']

    # Establish cross-account session
    print(f"Assuming Ops role for team {team_data['team-id']}")

    xa_session = quests_api_client.assume_team_ops_role(team_data['team-id'])

    client = boto3.client('elbv2', region_name="us-east-1")
    response = client.describe_load_balancers()
    for responses in response["LoadBalancers"]:
        print(responses["DNSName"])
        result=[]
        result.append(responses["DNSName"])
        for result in result:
            #print (result)
            data = {"user" : "<script><alert>Hello></alert></script>"}
            r = requests.post("http:" + "//" + result, data=data)
            print(r.status_code)
            parameter_value = r.status_code
            if r.status_code == 200:
                team_data["success-returned"] == False
            elif r.status_code == 504:
                team_data["success-returned"] == False
            elif r.status_code == 403:
                team_data["success-returned"] == True

            data1 = {"user" : "'AND 1=1;"}
            r = requests.post("http:" + "//" + result, data=data1)
            print(r.status_code)
            if r.status_code == 200:
                team_data["success-returned"] == False
            elif r.status_code == 504:
                team_data["success-returned"] == False
            elif r.status_code == 403:
                team_data["success-returned"] == True

            header = {"X-TomatoAttack" : "Red"}
            r = requests.post("http:" + "//" + result, headers=header)
            print(r.status_code)
            if r.status_code == 200:
                team_data["success-returned"] == False
            elif r.status_code == 504:
                team_data["success-returned"] == False
            elif r.status_code == 403:
                team_data["success-returned"] == True

            header2 = {"X-TomatoAttack" : "Red"}
            r = requests.post("http:" + "//" + result, headers=header2)
            print(r.status_code)
            if r.status_code == 200:
                team_data["success-returned"] == False
            elif r.status_code == 504:
                team_data["success-returned"] == False
            elif r.status_code == 403:
                team_data["success-returned"] == True



   

    if check_for_shell:
        print(f"Checking if team {team_data['team-id']} has launched their CloudShell")
        cloudtrail_client = xa_session.client('albv2')
        quest_start = datetime.datetime.fromtimestamp(team_data['quest-start-time'])
        alb_response = client.describe_load_balancers()
         
        # If there were any events, post the inputs, interim award 34% of the points and move on to the next stage
        print(f"CloudTrail lookup result for team {team_data['team-id']}: {alb_response}")
        if len(alb_response['Events']) > 0:
            team_data['succeed-returned'] = True
            quests_api_client.post_quest_interim_score(
                team_id=team_data['team-id'],
                quest_id=QUEST_ID,
                score_weighting=int(team_data['score-weight-progress'] + 34)
            )
            quests_api_client.post_input(
                team_id=team_data['team-id'],
                quest_id=QUEST_ID,
                key="status_code",
                label="What is the status code on running a curl?"
            )
            quests_api_client.post_input(
                team_id=team_data['team-id'],
                quest_id=QUEST_ID,
                key="parameterValue",
                label="Please input the status code you get on running a curl?"
            )
        else:
            print(f"No matching code  found for team {team_data['team-id']}")
    else:
        print(f"Checking inputs for team {team_data['team-id']}")
        if not team_data['correct-success-input']:
            team_data = evaluate_role_input(quests_api_client=quests_api_client, team_data=team_data)
        if not team_data['correct-parameter']:
            team_data = evaluate_parameter_input(quests_api_client=quests_api_client, team_data=team_data)

    # Check to see if everything is done
    if (team_data['success-input']
            and team_data['correct-success-input']
            and team_data['correct-parameter']):
        print(f"Team {team_data['team-id']} has completed this quest, posting output and awarding points")
        quests_api_client.post_output(
            team_id=team_data['team-id'],
            quest_id=QUEST_ID,
            key='quest_complete_1',
            label='Congratulations!',
            value="You've completed this Quest!",
            dashboard_index=4,
            markdown=True,
        )
        quests_api_client.post_quest_complete(team_id=team_data['team-id'], quest_id=QUEST_ID, weighting=100)


    # Either way, we re-persist team_data to DynamoDB to capture state changes
    dynamodb_response = icebreaker_status_table.put_item(Item=team_data)
    print(f"persisted team data back to {QUEST_TEAM_STATUS_TABLE}: {json.dumps(dynamodb_response)}")


def evaluate_role_input(quests_api_client, team_data):
    role_input = quests_api_client.get_input(
        team_id=team_data['team-id'],
        quest_id=QUEST_ID,
        key="status_code"
    )
    print(f"Evaluating role input for team {team_data['team-id']}: {json.dumps(role_input, default=str)}")
    # Check forgivingly, ignoring case
    if role_input['value'] is not None and role_input['value'].lower() == 'teamrole':
        print("Correct answer provided, awarding points.")
        team_data['success-returned'] = True
        team_data["paramater_value"] = 403
        quests_api_client.post_quest_interim_score(
            team_id=team_data['team-id'],
            quest_id=QUEST_ID,
            score_weighting=int(team_data['score-weight-progress'] + 30)
        )
        quests_api_client.post_output(
            team_id=team_data['team-id'],
            quest_id=QUEST_ID,
            key='role_input_complete_1',
            label='Success!',
            value="You've added the right controls here, here's some points!",
            dashboard_index=24,
            markdown=True,
        )
        quests_api_client.delete_output(
            team_id=team_data['team-id'],
            quest_id=QUEST_ID,
            key='role_input_incorrect_1'
        )

    
    else:
        print("Incorrect answer provided")
        quests_api_client.post_output(
            team_id=team_data['team-id'],
            quest_id=QUEST_ID,
            key='role_input_incorrect_1',
            label='Oops!',
            value="You need to madd more controls. Try again or use the hint for help.",
            dashboard_index=34,
            markdown=True,
        )

    return team_data


def evaluate_parameter_input(quests_api_client, team_data):
    parameter_input = quests_api_client.get_input(
        team_id=team_data['team-id'],
        quest_id=QUEST_ID,
        key="parameterValue"
    )
    print(f"Evaluating role parameter input for team {team_data['team-id']}: {json.dumps(parameter_input)}")
    # Check forgivingly, ignoring case
    if (parameter_input['value'] is not None
            and parameter_input['value'].lower() == team_data['parameter-value'].lower()):
        print("Correct answer provided, awarding points.")
        team_data['parameter_value'] = 504
        quests_api_client.post_quest_interim_score(
            team_id=team_data['team-id'],
            quest_id=QUEST_ID,
            score_weighting=int(team_data['score-weight-progress'] + 20)
        )
        quests_api_client.post_output(
            team_id=team_data['team-id'],
            quest_id=QUEST_ID,
            key='parameter_input_complete_1',
            label='You are Close!',
            value="Please add more controls, here's some points!",
            dashboard_index=24,
            markdown=True,
        )
        quests_api_client.delete_output(
            team_id=team_data['team-id'],
            quest_id=QUEST_ID,
            key='parameter_input_incorrect_1'
        )
    else:
        print("Incorrect answer provided")
        quests_api_client.post_output(
            team_id=team_data['team-id'],
            quest_id=QUEST_ID,
            key='parameter_input_incorrect_1',
            label='Oops!',
            value="You need to add more controls. Try again or use the hint for help.",
            dashboard_index=24,
            markdown=True,
        )

    return team_data
