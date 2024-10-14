# Revelio Labs Caching Assignment

The assignment focuses on creating an efficient system to process job listings to infer seniority for the roles based on a custom scale. The challenge involves setting up a caching layer to reduce expensive computation. 

## Considerations and Requirements

### Speed

8M per day -> ~5600 per minute -> ~93 per second so we are under the processing limit of 1000 per second, but in the interest of efficiency, implementing a caching service would be important.

Average gRPC lookups - 1.8B total job scraped/20M unique company, title combinations = 1.11% of listing. 
By implementing a caching mechanism we can reduce gRPC calls by over 98%, resulting in significantly faster performance.

Considering the performance requirements using a Redis database would provide the best performance with sub micro-second lookup times.

### Storage & Backup

Considering ~20M unique pairs with an estimated an average length of 50 characters and seniority levels stored as integers, it would take about 100 bytes of storage per record including overhead. That would total ~2GB database size, giving us plenty of room to scale in the future.

Redis database can be backed up to S3 daily to ensure that data can be restored in case of failures. This is important because Redis is an in-memory database and can be susceptible to data loss.

### Cost

If cost is a major concern, we have the option to self-host a redis instance or use a NoSQL database like DynamoDB which would be slightly slower, but cheaper to operate.

## Workflow

### Input

1. Read JSONL files containing the raw job postings can be read from `s3://rl-data/job-postings-raw/` through a Lambda trigger or setting up a SQS queue. The code will execute the entire pipeline of steps below. Sample code implementing an invoked Lambda job can be found in the `lambda_handler` function in [sample.py](/sample.py).

### Processing

1. Read JSONL files to extract company and post titles. Sample code can be found in the `read_jsonl_file_from_s3` function in [sample.py](/sample.py).
2. De-duplicate any potential listings to ensure we are processing each unique pair only once and minimizing redundant cache lookups and gRPC calls. Sample code can be found in the `deduplicate_job_postings` function in [sample.py](/sample.py).
3. Check Redis cache for each unique pair of (company, title). This is done to avoid duplicate keys in the cache. Sample code can be found in the `check_cache` function in [sample.py](/sample.py).
4. For each pair of (company, title) not present in Redis, we create a batch gRPC call to execute the Seniority model. Sample gRPC proto, code and Dockerfile to deploy the gRPC server can be found in [seniority_grpc](/seniority_grpc/) folder.
5. For the missing (company, title) pairs, we need to add them to the Redis cache for future lookups. Sample code can be found in the `update_cache` function in [sample.py](/sample.py).
6. Combine the results from cache hits and gRPC calls and augment the original job listing by adding the `seniority` key to each line. Sample code can be found in the `augment_job_postings` function in [sample.py](/sample.py).

### Output

1. Finally write the results to `s3://rl-data/job-postings-mod/` with the Seniority info. We have implemented an efficient caching mechanism to improve execution efficiency and reduced costs. 

## Potential future improvements

1. Setup SQS to poll the queue every minute to line up with new job.
2. If the Seniority model is updated then the Redis database can be cleared/updated through an adhoc run.
3. Move old raw JSONL files to cold storage after needed time to reduce storage costs. 
4. Hashing (company, title) pairs to reduce key size and storage costs.
