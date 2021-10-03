import boto3
import random
import cfn_response
import json


def lambda_handler(event, context):
    try:
        print(f"event: {json.dumps(event)}")
        print(f"context: {str(context)}")

        response_data = {}
        parameter_name = event['ResourceProperties']['ParameterName']

        ssm_client = boto3.client('ssm')

        if event['RequestType'] == 'Delete':
            try:
                ssm_client.delete_parameter(
                    Name=parameter_name
                )
                cfn_response.send(event, context, cfn_response.SUCCESS, response_data, parameter_name)
                return
            except Exception as e:
                cfn_response.send(event, context, cfn_response.FAILED, response_data, parameter_name)
                print(f"Custom resource lambda execution for delete has failed: {e}")
                return
        else:  # request type is create or update
            try:
                parameter_value = f"Unicorn.Rentals-{random.randint(1000,9999)}"
                ssm_client.put_parameter(
                    Name=parameter_name,
                    Description="Parameter for you to find in your icebreaker challenge!",
                    Value=parameter_value,
                    Overwrite=True,
                    Tier="Standard",
                    Type="String",
                    DataType="text"
                )
                response_data['value'] = parameter_value
                response_data['name'] = parameter_name
                cfn_response.send(event, context, cfn_response.SUCCESS, response_data, parameter_name)
                return
            except Exception as e:
                cfn_response.send(event, context, cfn_response.FAILED, response_data, parameter_name)
                print(f"Lambda execution has failed! Parameter was not created: {e}")
                return

    except Exception as e:
        cfn_response.send(event, context, cfn_response.FAILED, {}, None)
        print(f"Lambda execution has failed unexpectedly, unknown request type (probably a debugging code issue): {e}")
        return
