import json
import math
import os
from tqdm import tqdm

import numpy as np
import openai
from dotenv import load_dotenv
from openai.embeddings_utils import cosine_similarity

import src.helpers.StringMatchHelp

with open("data/memories.json", 'r') as f:
    mems = json.load(f)

MODEL = "text-embedding-ada-002"
load_dotenv()


def _getEmbedding(s):
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    res = openai.Embedding.create(input=s, model=MODEL)['data'][0]['embedding']
    return res

def calculate_output(weights, inputs):
    # calculate output based on weights and inputs
    _, perc, _, _ = src.helpers.StringMatchHelp.fuzzyMatchString(inputs[0], inputs[1], weights=weights)
    return perc

def optimize_weights(inputs: list[tuple[str, str]], num_weights, expected_outputs, epochs=1000):
    best_weights = []
    best_difference = math.inf

    for i in tqdm(range(epochs)):
        r_weights = np.random.rand(num_weights)
        sum_differences = 0
        for i, input in enumerate(inputs):
            x = calculate_output(r_weights, input)
            sum_differences += abs(expected_outputs[i] - x)
        if sum_differences < best_difference:
            print(f"Got new best weights: {r_weights} = {sum_differences} diff")
            best_difference = sum_differences
            best_weights = r_weights

    return best_weights

l = []
l2 = []
embeds = [_getEmbedding(m) for m in mems]
expected_outputs = []
inputs = []
for i, a in enumerate(embeds):
    for j, b in enumerate(embeds[i + 1:]):
        k = j + i + 1
        inputs.append((mems[i], mems[k]))
        cos_sim = cosine_similarity(a, b)
        l.append((cos_sim, mems[i], mems[k]))
        expected_outputs.append(cos_sim)
        _, perc, _, _ = src.helpers.StringMatchHelp.fuzzyMatchString(mems[i], mems[k])
        l2.append((perc, mems[i], mems[k]))

new_weights = optimize_weights(inputs, 4, expected_outputs, epochs=1000)
print("Best weights: ", new_weights)
l3 = []
for i, a in enumerate(embeds):
    for j, b in enumerate(embeds[i + 1:]):
        k = j + i + 1
        _, perc, _, _ = src.helpers.StringMatchHelp.fuzzyMatchString(mems[i], mems[k], weights=new_weights)
        l3.append((perc, mems[i], mems[k]))

l = sorted(l, key=lambda x: x[0], reverse=True)
l2 = sorted(l2, key=lambda x: x[0], reverse=True)
l3 = sorted(l3, key=lambda x: x[0], reverse=True)


for m in l:
    print(f"{m[0]}: {m[1]} vs {m[2]}")

print("---------------OLDWEIGHTS---------------")
for m in l2:
    print(f"{m[0]}: {m[1]} vs {m[2]}")
print("--------------NEWWEIGHTS---------------")
for m in l3:
    print(f"{m[0]}: {m[1]} vs {m[2]}")


#Best: [0.001, 2, 9, 0.1]

