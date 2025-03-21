# from execute_nuxmv import LTL2SMV, nuXmv_ic3
import re
import os
import random
from tqdm import trange
import argparse
import subprocess
import timeout_decorator

Parse = argparse.ArgumentParser()
Parse.add_argument('-i', type=int, default=0, help="The LTL formulae file to be parsed!")
Parse.add_argument('-toS', type=int, default=5, help="The LTL formulae file to be parsed!")
args = Parse.parse_args()
# FILENAMES = ["AAP", "ATM", "Ele", "LAS", "MP", "PA", "RP1", "RP2", "RRCS", "TCP", "Tel"]
FILENAMES = ["RP2"]
# FILENAMES = [FILENAMES[args.i]]
# FILENAMES = ["ATM"]
APPROACHS = ["Tab_aalta", "GA_aalta", "LOGION"]
# APPROACHS = ["Tab_aalta", "Tab_nuXmv","GA_aalta" , "GA_nuXmv"]
# APPROACHS = ["LOGION"]
TIMES = 10

def LTL2SMV(formulae:str, vocab=[f'p{i}' for i in range(100)], smv_file='./temp/1tempfile'):
    content = "MODULE main\nVAR\n"
    for v in vocab:
        content += v + ':boolean;\n'

    content += 'LTLSPEC!(\n' + formulae + ')'

    with open(smv_file, 'w') as smvfile:
        smvfile.write(content)

def nuXmv_ic3(temp_uc_path:str):

    #nuXmv_ic3求解
    cmd = './nuXmv -int'
    # -d is optional
    lines = [
        f"read_model -i {temp_uc_path}\n",
        "flatten_hierarchy\n",
        "encode_variables\n",
        "build_boolean_model\n",
        "check_ltlspec_ic3\n",
        "quit\n"
    ]
    # results = os.popen(f'{cmd}\n{lines}').readlines()
    # for result in results:
    #     if(result.readlines().find("is false") != -1):
    #         print("1")
    #         return True
    #     else:
    #         return False
    stdin_sat_solver = ''.join(lines).encode()
            #     # endwith
            # # endif
            # cur_time = time.time()
    mytask = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
    try:
        mytask.stdin.write((stdin_sat_solver))
        result,err = mytask.communicate(timeout= args.toS)
        # print(result.decode())
        if(result.decode().find("is false") != -1):
            return True
        else:
            return False
    except Exception as e:
        mytask.kill()
        return False
def Parse(ltl:str):
    vocab = []
    token = list(set(re.findall(r'[_a-zA-Z][_a-zA-Z0-9]*', ltl)))
    del_token = ['X', 'G', 'F', 'U', 'W']
    for dt in token:
        if(dt not in del_token):
            vocab.append(dt)
    replaces = {'~':'!', '||':'|', '&&':'&', '<>':'F', '[]':'G', 'W':'R', 'True':'TRUE', 'false':'FALSE', 'False':'FALSE'}
    for i in replaces:
        ltl = ltl.replace(i, replaces[i])
    return vocab, ltl

def Gen_BCs(BCs:list, pid:int):
    gen_BCs = []
    nuxmvs = []
    leng = len(BCs)
    for bc1 in BCs:
        flag = True
        vocab1, bc1 = Parse(bc1)
        nuxmv = []
        for bc2 in BCs:
            if(bc1==bc2):
                nuxmv.append(False)
                continue
            vocab2, bc2 = Parse(bc2)
            vocab = list(set(vocab1+vocab2))
            ltl1 = f'!(({bc1}) -> ({bc2}))'
            temp = f'./temp/{pid}.txt'
            LTL2SMV(ltl1, vocab, temp)
            SAT = nuXmv_ic3(temp)
            nuxmv.append(SAT)
            # print(ltl1, SAT)
        nuxmvs.append(nuxmv)
    # print(nuxmvs)
    for i in range(leng):
        flag = True
        for j in range(leng):
            if(j==i):continue
            if(nuxmvs[j][i] and not nuxmvs[i][j]):
                flag = False
                break
        if(flag):
            gen_BCs.append(BCs[i])
    return gen_BCs  
               
split = 10
def multi_gen_BCs(BCs:list, pid:int):
    if(len(BCs)<split):
        return Gen_BCs(BCs, pid)
    leng = int(len(BCs)/2)
    # print(leng)
    return Gen_BCs(multi_gen_BCs(BCs[:leng], pid) + multi_gen_BCs(BCs[leng:], pid), pid)
# def multi_gen_BCs(BCs:list, split:int):
#     leng = int(len(BCs)/split)
#     BCsn =[]
#     for i in trange(split, ncols=80):
#         BC =[]
#         if(leng*(i+1)>len(BCs)): BC = BCs[leng*i:]
#         else: BC = BCs[leng*i:leng*(i+1)]
#         BCsn +=Gen_BCs(BC)
#         print(len(BCsn))
#     print(len(BCsn))
#     return BCsn

def read_LOGION(file_path:str):
    # gen_BCs = []
    pid = os.getpid()
    with open(file_path+".bc","r") as f:
        datas = f.readlines()
        BCs = []
        bc_length = int(datas[0][datas[0].find("BC: ")+4:])
        # print(datas[-1])
        for data in datas[1:]:
            BCs.append(data[data.find("LTL: ")+5:].replace("\n", ""))
    # l1 = 0
    random.shuffle(BCs)
    # while(len(BCs)-l1 < 20):
    #     l1=len(BCs)
    #     BCs.shuffle()
    #     split = int(len(BCs)/30)
    #     if(split==0):split=1
    #     BCs=multi_gen_BCs(BCs, split)
    gen_BCs = multi_gen_BCs(BCs, pid)
    BCs_file = file_path+ "gen.txt"
    # if not os.path.exists(BCs_file):
    with open(BCs_file, 'w') as fw:
            for i in gen_BCs:
                fw.write(i+"\n")
    return gen_BCs, bc_length, 0
def read_Tab(file_path:str):
    gen_BCs = []
    pid = os.getpid()
    with open(file_path+".txt","r") as f:
        datas = f.readlines()
        BCs = []
        if(file_path.find("nuXmv")!=-1):
            bc_length = int(datas[0][datas[0].find("#BCs:")+5:])
        bc_length = int(datas[0][datas[0].find("#BCs: ")+6:])
        # print(file_path, len(datas), datas[0], datas[-1])
        Time = float(datas[-1][datas[-1].find("(secs) ")+7:-2])
        for i in range(bc_length):
            if(file_path.find("nuXmv")!=-1):
                BCs.append(datas[2+i].replace("\n", ""))
            else:
                BCs.append(datas[3+i].replace("\n", ""))
    gen_BCs = Gen_BCs(BCs, pid)
    BCs_file = file_path + "gen.txt"
    # if not os.path.exists(BCs_file):
    with open(BCs_file, 'w') as fw:
            for i in gen_BCs:
                fw.write(i+"\n")
    return gen_BCs, bc_length, Time                
def read_GA(file_path:str):
    gen_BCs = []
    pid = os.getpid()
    with open(file_path+".txt","r") as f:
        datas = f.readlines()
        BCs = []
        # print(file_path, len(datas), datas[0], datas[-11])
        try:
            bc_length = int(datas[-11][11:datas[-11].find(", Total")])
        except Exception as e:
            bc_length = int(datas[-10][11:datas[-10].find(", Total")])
        for i in range(bc_length):
            BCs.append(datas[-13-i].replace("\n", ""))
    # for bc in BCs:
    #     print(bc)
    gen_BCs = multi_gen_BCs(BCs, pid)
    BCs_file = file_path+ "gen.txt"
    # if not os.path.exists(BCs_file):
    with open(BCs_file, 'w') as fw:
            for i in gen_BCs:
                fw.write(i+"\n")
    return gen_BCs, bc_length, 0

def execute():
    GENts = []
    for file in FILENAMES:
        GENt = [0 for i in range(len(APPROACHS))]
        for times in trange(TIMES):
            datas_BCs = []
            # datas_bc_lengths = []
            # datas_Times = []
            GEN = []
            for approach in APPROACHS:
                file_path = f'./data/{file}/{approach}/exec_{times}gen.txt'
                with open(file_path, 'r') as f:
                    datas_BCs.append(f.readlines())
                # if(approach.find("Tab") !=-1):
                    # Gen_BCs, bc_length, Time = read_Tab(file_path)
                    # datas_BCs.append(Gen_BCs)
                    # datas_bc_lengths.append(bc_length)
                    # datas_Times.append(Time)
                    # print(Gen_BCs, bc_length)
                # elif(approach.find("GA") !=-1):
                    # Gen_BCs, bc_length, Time = read_GA(file_path)
                    # datas_BCs.append(Gen_BCs)
                    # datas_bc_lengths.append(bc_length)
                    # datas_Times.append(Time)
                # else:
                    # Gen_BCs, bc_length, Time = read_LOGION(file_path)
                    # datas_BCs.append(Gen_BCs)
                    # datas_bc_lengths.append(bc_length)
                    # datas_Times.append(Time)
            for i in range(len(APPROACHS)):
                gen = 0
                BCs1 = datas_BCs[i]
                for bc1 in BCs1:
                    flag = True
                    vocab1, bc1 = Parse(bc1)
                    for j in range(len(APPROACHS)):
                        if(i==j):continue
                        BCs2 = datas_BCs[j]
                        flag2 = False
                        # print(BCs1, BCs2)
                        for bc2 in BCs2:
                            vocab2, bc2 = Parse(bc2)
                            vocab = list(set(vocab1+vocab2))
                            ltl1 = f'!({bc1}) -> ({bc2})'
                            ltl2 = f'!({bc2}) -> ({bc1})'
                            pid = os.getpid()
                            temp1 = f'./temp/{pid}1'
                            temp2 = f'./temp/{pid}2'
                            LTL2SMV(ltl1, vocab, temp1)
                            LTL2SMV(ltl2, vocab, temp2)
                            if(nuXmv_ic3(temp2) and not nuXmv_ic3(temp1)):
                                flag = False
                                flag2 = True
                                break
                        if(flag2):
                            break
                    if(flag):
                        gen += 1
                GEN.append(gen)
            for ele in range(len(GEN)):
                GENt[ele] += GEN[ele]
        print(file, GENt[0], GENt[1], GENt[2])
    
    
    # for i in range(len(FILENAMES)):
    #     gens = [0 for i in rnage(len(APPROACHS))]
    #     for j in range(TIMES):
    #         for k in range(len(APPROACHS)):
    #             gens[k] = gens[k] + GENts[i][j][k]
    #     print(FILENAMES[i], "Tab_aalta", "Tab_nuXmv","GA_aalta", "GA_nuXmv", "LOGION:", gens[0]/TIMES, gens[1]/TIMES, gens[2]/TIMES, gens[3]/TIMES, gens[4]/TIMES)


    
if __name__=="__main__":
    GEN = execute()