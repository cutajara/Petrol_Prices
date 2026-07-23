# Petrol_Prices
Forecast VIC Petrol Prices

Application runs in AWS to select data from inputs sources and store in database. Streamlit app to run the front end for users.

```mermaid
graph TD
    %% Define Styles
    classDef github fill:#24292e,stroke:#fff,stroke-width:1px,color:#fff;
    classDef awsOrange fill:#FF9900,stroke:#232F3E,stroke-width:1px,color:#232F3E;
    classDef awsGreen fill:#3F8624,stroke:#232F3E,stroke-width:1px,color:#fff;
    classDef awsBlue fill:#1A73E8,stroke:#232F3E,stroke-width:1px,color:#fff;
    classDef awsPurple fill:#8C4FFF,stroke:#232F3E,stroke-width:1px,color:#fff;
    classDef external fill:#5A6B7C,stroke:#232F3E,stroke-width:1px,color:#fff;
    classDef streamlit fill:#FF4B4B,stroke:#232F3E,stroke-width:1px,color:#fff;

    %% External Sources
    ServoAPI([Servo Saver API<br>Fuel Prices]):::external
    YFinance([yfinance<br>Brent · AUD/USD · DXY]):::external

    %% GitHub
    subgraph GitHub_Platform ["GitHub"]
        GA[GitHub Actions<br>Update Lambdas]:::github
    end

    %% AWS Cloud
    subgraph AWS_Cloud ["AWS — ap-southeast-2 (Sydney)"]

        EB[Amazon EventBridge<br>Cron Scheduler]:::awsOrange
        ECR[(Amazon ECR<br>Docker Registry)]:::awsPurple

        subgraph Lambdas ["Lambda Functions"]
            L1[petrol-poller]:::awsGreen
            L2[market-data]:::awsGreen
        end

        subgraph VPC ["VPC — petrol-predictor-vpc"]
            subgraph Subnets ["Private Subnets (ap-southeast-2a · 2b)"]
                RDS[(RDS PostgreSQL<br>petrol_predictor<br>db.t3.micro)]:::awsBlue
            end
        end

        IGW[Internet Gateway]:::awsOrange

    end

GA --> ECR
ECR --> L1
ECR --> L2

    %% External → Lambda
    ServoAPI -->|Fuel price data| L1
    YFinance -->|Market data| L2

    %% EventBridge → Lambda
    EB -->|Every 6h| L1
    EB -->|Every 24h| L2



    %% Lambda → RDS via IGW
    L1 -->|Insert prices| IGW
    L2 -->|Insert market data| IGW
    IGW --> RDS


    
    %% Streamlit → RDS
    Streamlit -->|SELECT only · streamlit_readonly| IGW
    User -->|Browser| Streamlit
```

## Input Sources:
- VIC Servo Saver API
- Financial market data from ```yfinance``` package

## Flow
- EventBridge schedules Lambda functions to select the data and insert into RDS Postgres database
- The Lambda environment runs as in image which is stored in ECR, this is updated with Github actions on changes to main.
- Secrets manager stores the keys
- CloudWatch alarms are set to notify of errors via SNS

## Next Steps
- Develop a model to forecast petrol prices
- Serve this to a website for the public


# Supabase
Flow was orignally run with Github actions and Supabase. This has been mirgated to AWS. The supabase and Github actions runs are still supported at the moment.
