import boto3
import json
import redis
import grpc
from seniority_grpc import SeniorityModel_pb2
from seniority_grpc import SeniorityModel_pb2_grpc


s3 = boto3.client('s3')
redis_client = redis.Redis(host='local-host',port=12252,password='xxxx')
channel = grpc.insecure_channel('localhost:50051')
stub = SeniorityModel_pb2_grpc.SeniorityModelStub(channel)

def read_jsonl_file_from_s3(bucket_name, file_key):
    """
    Reads a JSONL file from S3 and returns a list of job postings (dict).
    """
    obj = s3.get_object(Bucket=bucket_name, Key=file_key)
    lines = obj['Body'].read().decode('utf-8').splitlines()
    job_postings = [json.loads(line) for line in lines]
    return job_postings

def deduplicate_job_postings(job_postings):
    """
    Deduplicates the job postings based on (company, title).
    Returns a set of unique (company, title) tuples.
    """
    unique_pairs = {(job['company'], job['title']) for job in job_postings}
    return unique_pairs

def check_cache(unique_pairs):
    """
    Check Redis cache for (company, title) pairs.
    Returns a dictionary with cache hits and cache misses.
    """
    cache_hits = {}
    cache_misses = {}
    uuid_counter = 0
    
    for company, title in unique_pairs:
        cache_key = f"{company}:{title}"
        seniority = redis_client.get(cache_key)
        
        if seniority:
            cache_hits[(company, title)] = int(seniority)
        else:
            cache_misses[uuid_counter]= (company, title)
            uuid_counter+=1
    
    return cache_hits, cache_misses

def grpc_infer_seniority(cache_misses):
    """
    Calls the gRPC endpoint for all cache misses.
    Returns a dictionary with seniority levels for the given (company, title) pairs.
    """
    seniority_request_batch = SeniorityModel_pb2.SeniorityRequestBatch(
        batch=[SeniorityModel_pb2.SeniorityRequest(uuid=uuid, company=value[0], title=value[1]) for uuid, value in cache_misses.items()]
    )
    
    response = stub.InferSeniority(seniority_request_batch)
    seniority_dict = {(cache_misses[resp.uuid][0], cache_misses[resp.uuid][1]): resp.seniority for resp in response.batch}
    
    return seniority_dict

def update_cache(seniority_dict):
    """
    Update Redis cache with the inferred seniority levels.
    """
    for (company, title), seniority in seniority_dict.items():
        cache_key = f"{company}:{title}"
        redis_client.set(cache_key, seniority) 

def augment_job_postings(job_postings, seniority_info):
    """
    Augment each job posting with the corresponding seniority level.
    """
    for job in job_postings:
        company_title_pair = (job['company'], job['title'])
        job['seniority'] = seniority_info.get(company_title_pair, None)  # Assign seniority if available
    
    return job_postings

def write_to_s3(bucket_name, file_key, augmented_data):
    """
    Write augmented job postings to S3 as JSONL.
    """
    output_lines = [json.dumps(job) for job in augmented_data]
    output_body = "\n".join(output_lines)
    
    s3.put_object(Bucket=bucket_name, Key=file_key, Body=output_body)

def process_file(bucket_input, bucket_output, file_key):
    # Step 1: Read the JSONL file
    job_postings = read_jsonl_file_from_s3(bucket_input, file_key)
    
    # Step 2: Deduplicate (company, title) pairs
    unique_pairs = deduplicate_job_postings(job_postings)
    
    # Step 3: Check cache
    cache_hits, cache_misses = check_cache(unique_pairs)
    
    # Step 4: Call gRPC for cache misses
    if cache_misses:
        grpc_results = grpc_infer_seniority(cache_misses)
        # Step 5: Update cache with gRPC results
        update_cache(grpc_results)
    else:
        grpc_results = {}
    
    # Combine cache hits and gRPC results
    seniority_info = {**cache_hits, **grpc_results}
    
    # Step 6: Augment job postings with seniority information
    augmented_postings = augment_job_postings(job_postings, seniority_info)
    
    # Step 7: Write augmented data to output S3 bucket
    output_file_key = f"rl-data/job-postings-mod/{file_key}"
    write_to_s3(bucket_output, output_file_key, augmented_postings)

def lambda_handler(event, context):
    """
    AWS Lambda function triggered by S3 file uploads. Processes the newly uploaded files.
    """
    # Extract bucket and file key from the event
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        file_key = record['s3']['object']['key']
        
        # Process the file
        process_file(bucket, 'rl-data', file_key)