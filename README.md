import boto3

client = boto3.client('ec2')

response = client.describe_instances(
Filters=[
        {
            'Name': 'tag:MyTag1',
            'Values': [
                'Test1',
            ]
        },
    ],
)

print response
print len(response['Reservations'])

noofinstances = 0

allreservations = response['Reservations']

for eachreservation in allreservations:

    allinstancesinreservation = eachreservation['Instances']
    #noofinstances += len(allinstancesinreservation)

    for eachinstanceinreservation in allinstancesinreservation:
        if eachinstanceinreservation['State']['Name'] == 'running':
            print eachinstanceinreservation
            noofinstances += 1


print noofinstances
