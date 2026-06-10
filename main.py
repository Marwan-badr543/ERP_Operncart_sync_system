import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.controller.endpoints:app", host='localhost', port=8000 )
    
# update the host to '0.0.0.0' in production    


# http://your-ip-address:8000/test

