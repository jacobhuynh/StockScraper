import os
import sys
import time
import django
import discord
import asyncio
from discord.ext import commands

import io
import json
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes, VisualFeatureTypes
import requests
from PIL import Image, ImageDraw, ImageFont

import openai

from stockscrapper import getStockDataArray

from django.shortcuts import get_object_or_404
from asgiref.sync import sync_to_async

# setup django connection
parent_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(parent_dir)
sys.path.append(project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from discord_stock_bot.models import *

# setup microsoft azure computer vision ai
credentials = json.load(open('discord_bot/credentials.json'))
API_KEY = credentials['API_KEY']
ENDPOINT = credentials['ENDPOINT']

cv_client = ComputerVisionClient(ENDPOINT, CognitiveServicesCredentials(API_KEY))

# setup open ai api
OPENAI_KEY = credentials['OPENAI_KEY']
openai.api_key = OPENAI_KEY

# discord bot
TOKEN = credentials['TOKEN']

bot = commands.Bot(command_prefix="!", intents = discord.Intents.all())

@bot.event
async def on_ready():
    print("ready")
    
@bot.command(name="mystocks")
async def mystocks(context):
    if await sync_to_async(Users.objects.filter(discord_id=str(context.author)).exists)():
        user = await sync_to_async(Users.objects.get)(discord_id=context.author)
        await context.send("Your current stocks: " + user.stock_list)
    else:
        await context.send("You have no stocks yet.")
    
@bot.command(name="uploadstocks")
async def uploadstocks(context):
    await context.send("Upload an image within 60 seconds.")
    
    # check if same user sent image
    def check(message):
        return message.author == context.author and len(message.attachments) > 0 and message.channel == context.channel
    
    try:
        # timeout user if over 60 seconds
        message = await bot.wait_for("message", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await context.send("You did not send an image within 60 seconds.")
    else:
        try:
            # get image url from discord
            image_url = message.attachments[0].url
            
            # upload image to azure
            cv_response = cv_client.read(url = image_url, language = 'en', raw=True)
            operation_location = cv_response.headers['Operation-Location']
            operation_id = operation_location.split('/')[-1]
            result = cv_client.get_read_result(operation_id)
            
            final_read = ""
            
            print(result.status)
            print(result.analyze_result)
            
            while True:
                result = cv_client.get_read_result(operation_id)
                if result.status not in [OperationStatusCodes.not_started, OperationStatusCodes.running]:
                    break 
                print("Operation running")
                time.sleep(1)
            
            if result.status == OperationStatusCodes.succeeded:
                read_results = result.analyze_result.read_results
                for analyzed_result in read_results:
                    for line in analyzed_result.lines:
                        final_read += " " + line.text
                await context.send("Analyzing Image.")
                
                # send to openai api to get back stock tickers
                openai_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "user", 
                        "content":final_read + " Extract the stock tickers of the companies, and output ONLY the stock tickers and format it in a string separated by commas and a single space with no text other than the tickers. Example: AMZN, META, GOOGL"
                        }
                    ]
                )
                await context.send("Finding Stock Tickers.")
                
                
                # use yahoo stock scrapper to get stock data
                stock_list = openai_response['choices'][0]['message']['content'].strip("\n").strip().split(", ")
                print(stock_list)
                stock_data_list = []
                
                # add user to database
                if await sync_to_async(Users.objects.filter(discord_id=message.author).exists)():
                    user = await sync_to_async(Users.objects.get)(discord_id=message.author)
                    user.stock_list = openai_response['choices'][0]['message']['content'].strip("\n").strip()
                    await sync_to_async(user.save)()
                else:
                    await sync_to_async(Users.objects.create)(discord_id = message.author, stock_list = openai_response['choices'][0]['message']['content'].strip("\n").strip())
                
                await context.send("Gathering Data.")
                for stock in stock_list:
                    stock_data_list.append(getStockDataArray(stock))
                    
                # send to openai api to get back stock analysis
                for stock in stock_data_list:
                    stock_data_string = ', '.join(stock)
                    print(stock_data_string)
                    openai_response2 = openai.ChatCompletion.create(
                        model="gpt-4-0125-preview",
                        messages=[
                            {"role": "user", 
                            "content":"I have a portfolio of stocks and need detailed analysis and advice on each. Each stock will be formatted as follows: 'Symbol, Price, Change, Percent Change, Yahoo Estimated Return'. Here is one of the stocks and it's respective data: " + stock_data_string + "You must format it like so: **Company Name (Ticker)** (statistics listed in bullet points) **Analysis** (newline, analysis) **Advice** (newline, advice) and nothing else. It is dire that you keep it LESS THAN 2000 CHARACTERS or I will die, so ensure that your response is 2000 characters or less."
                            }
                        ]
                    )
                    await context.send(openai_response2['choices'][0]['message']['content'].strip("\n").strip())
            else:
                await context.send("Could not process image: " + image_url)
        except Exception as e:
            await context.send("An error occured. Please try again.")
    
bot.run(TOKEN)