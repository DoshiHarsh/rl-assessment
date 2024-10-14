import grpc

# import the generated classes
import SeniorityModel_pb2
import SeniorityModel_pb2_grpc

# open a gRPC channel
channel = grpc.insecure_channel('localhost:50055')

# create a stub (client)
stub = SeniorityModel_pb2_grpc.SeniorityModelStub(channel)

# create a valid request message
seniority_request_batch = SeniorityModel_pb2.SeniorityRequestBatch(
        batch=[SeniorityModel_pb2.SeniorityRequest(uuid=16,company=f"fds{i}",title="vfe") for i in range(5)]
    )

# make the call
response = stub.InferSeniority(seniority_request_batch)

# et voilà
print({(resp.uuid, resp.seniority) for resp in response.batch})
