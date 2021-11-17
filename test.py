import datetime
# print(type(datetime.datetime.now().date()))
# print(datetime.datetime.now())
# order_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + "%09d"%3
# print(order_id)

# import base64
# import pickle
# test_dict = {1:{'id':5,'count':8},2:{'id':7,'count':3}}
# test_p = pickle.dumps(test_dict)
# test_b = base64.b64encode(test_p)
# test_str = test_b.decode()
# print(test_str) # gAN9cQAoSwF9cQEoWAIAAABpZHECSwVYBQAAAGNvdW50cQNLCHVLAn1xBChoAksHaANLA3V1Lg==
# test_str = 'gAN9cQAoSwF9cQEoWAIAAABpZHECSwVYBQAAAGNvdW50cQNLCHVLAn1xBChoAksHaANLA3V1Lg=='
# test_b = test_str.encode()
# # print(test_b)
# test_p = base64.b64decode(test_b)
# # print(test_p)
# test_dict = pickle.loads(test_p)
# # print(test_dict)

# import os
# print("8"*10)
# print(__file__)
# print(os.path.abspath(__file__))
# mypath = os.path.join('name',*['zx','hj','cx'])
# print(mypath)

from datetime import datetime
mytime1 = datetime.strptime("2021-11-16","%Y-%m-%d").date()
mytime2 = datetime.now().date()
print(mytime1,mytime2)
print(mytime1 == mytime2)