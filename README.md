# Petrol_Prices
Forecast VIC Petrol Prices

**Live Site:** [https://petrolprices-vic.streamlit.app/](https://petrolprices-vic.streamlit.app/)

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

    GA -->|Push to main| Streamlit

    %% AWS Cloud
    subgraph AWS_Cloud ["AWS — ap-southeast-2 (Sydney)"]

        EB[Amazon EventBridge<br>Cron Scheduler]:::awsOrange
        ECR[(Amazon ECR<br>Docker Registry)]:::awsPurple

        subgraph Lambdas ["Lambda Functions"]
            L1[petrol-poller]:::awsGreen
            L2[market-data]:::awsGreen
            L3[train-model]:::awsGreen
            L4[predict-model]:::awsGreen
        end
        RDS[(RDS Aurora \n PostgreSQL)]:::awsBlue
        S3[(S3 Bucket<br>Model Storage)]:::awsBlue
        
        

    end

    Streamlit([Streamlit App<br>Front End]):::streamlit
    User([User<br>Browser]):::external

    %% GitHub → AWS

GA --> ECR
ECR --> L2

    %% External → Lambda
    ServoAPI -->|Fuel price data| L1
ECR --> L1

    %% EventBridge → Lambda
    EB -->|Every 24h| L2
    EB -->|Every 6h| L1
    EB -->|Every 24h| L3
    EB -->|Every 24h| L4

    YFinance -->|Market data| L2

    RDS --> L3
    L3 --> S3

    RDS --> L4
    S3 --> L4
    L4 --> RDS


    %% Lambda → RDS
    L1 -->|Insert prices| RDS
    L2 -->|Insert market data| RDS



    
    %% Streamlit → RDS
    Streamlit -->|SELECT only · streamlit_readonly| RDS
    User -->|Browser| Streamlit
```

## Input Sources:
- [VIC Servo Saver API](https://service.vic.gov.au/find-services/transport-and-driving/servo-saver)
- Financial market data from ```yfinance``` package

## Flow
- EventBridge schedules Lambda functions to select the data and insert into RDS database
- The Lambda environment runs as in image which is stored in ECR, this is updated with Github actions on changes to main.
- Models are trained and stored in S3
- Predictions write to the database and allow the Streamlit app to read the requirement data
- CloudWatch alarms are set to notify of errors via SNS
