using System;
using System.IO;
using System.Text;
using System.Net;
using System.Threading.Tasks;
using Npgsql;
using Newtonsoft.Json;
using Amazon;
using Amazon.Lambda.Core;
using Amazon.Lambda.APIGatewayEvents;
using Amazon.SecretsManager;
using Amazon.SecretsManager.Model;

[assembly: LambdaSerializer(typeof(Amazon.Lambda.Serialization.SystemTextJson.DefaultLambdaJsonSerializer))]

namespace LambdaDemo;

class DBSecret
{
	public string? DB_HOST;
       	public string? DB_USERNAME;
	public string? DB_PASSWORD;
	public string? DB_NAME;
}

public class Function
{
     
        public async Task<APIGatewayProxyResponse> FunctionHandler(APIGatewayProxyRequest request)	
        {
	    string region = Environment.GetEnvironmentVariable("AWS_REGION");
	    
	    string secretName = Environment.GetEnvironmentVariable("SECRET_NAME");

            IAmazonSecretsManager client = new AmazonSecretsManagerClient(RegionEndpoint.GetBySystemName(region));

	    GetSecretValueRequest secretRequest = new GetSecretValueRequest
    	    {
        	SecretId = secretName,
    	    };

	    GetSecretValueResponse secretResponse;

	    try
    	    {
        	secretResponse = await client.GetSecretValueAsync(secretRequest);
    	    }
            catch (Exception e)
    	    {
        	throw e;
    	    }

    	    string secret = secretResponse.SecretString;

	    Console.WriteLine("The Secret is successfully retreated from Secrets Manager");

	    DBSecret credentials = JsonConvert.DeserializeObject<DBSecret>(secret);

	    string pageData =
                "<!DOCTYPE>" +
                "<html>" +
                "  <head>" +
                "    <title>HttpListener Example</title>" +
                "  </head>" +
                "  <body>" +
                "    <p>Welcome to .NET Server (c) Ignat Strelets</p>" +
                "  </body>" +
                "</html>";	
            string dbHost = credentials.DB_HOST;
            string dbUsername = credentials.DB_USERNAME;
            string dbPassword = credentials.DB_PASSWORD;
            string dbName = credentials.DB_NAME;
    
            string connectionString = string.Format("Host={0};Port=5432;Username={1};Password={2};Database={3};",dbHost,dbUsername,dbPassword,dbName);
            NpgsqlConnection connection = new NpgsqlConnection(connectionString);
            
            Console.WriteLine(connectionString);

            try
            {
                connection.Open();
                Console.WriteLine("Connected to PostgreSQL!");
    
                Console.WriteLine("Postgres Version:");
                Console.WriteLine(connection.PostgreSqlVersion);
		connection.Close();
    
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
            }


                return new APIGatewayProxyResponse
		{
	            StatusCode = 200,
                    Body = pageData,
		    Headers = new Dictionary<string, string> { {"Content-Type", "text/html"} }	    
		};	    
	}
}
