import grpc
from concurrent import futures
import time
import random

# import the generated classes
import SeniorityModel_pb2
import SeniorityModel_pb2_grpc


# create a class to define the server functions, derived from
# calculator_pb2_grpc.CalculatorServicer
class SeniorityModelServicer(SeniorityModel_pb2_grpc.SeniorityModelServicer):


    def InferSeniority(self, request, context):
        
        response_batch = SeniorityModel_pb2.SeniorityResponseBatch()
        
        for req in request.batch:
            response = SeniorityModel_pb2.SeniorityResponse()
            response.uuid = req.uuid
            response.seniority = random.randint(1,7)
            response_batch.batch.append(response)
        
        return response_batch



# create a gRPC server
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

# use the generated function `add_CalculatorServicer_to_server`
# to add the defined class to the server
SeniorityModel_pb2_grpc.add_SeniorityModelServicer_to_server(
        SeniorityModelServicer(), server)

# listen on port 50053
print('Starting server. Listening on port 50055.')
server.add_insecure_port('[::]:50055')
server.start()

# since server.start() will not block,
# a sleep-loop is added to keep alive
try:
    while True:
        time.sleep(86400)
except KeyboardInterrupt:
    server.stop(0)
