from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import random

SPLIT_CHAR = '\t'
PARTIAL_RATIO_MIN = 70
RATIO_MIN = 60
TOKEN_SET_MIN = 70
TOKEN_SORT_MIN = 70
AVERAGE_MIN = 70
PROB_MIN = 0.7


class ResponseHandler(object):
    responseFile = ""
    botNoResponse = ""

    def __init__(self, responseFile, botNoResponse):
        self.responseFile = responseFile
        self.botNoResponse = botNoResponse

    async def addResponse(responseFile, newTrigger, newResponse):
        triggerMatch = False
        with open(responseFile, 'r') as responses:
            lines = responses.readlines()

        for i in range(len(lines)):
            words = lines[i].split(SPLIT_CHAR, 1)
            trigger = words[0]

            # add new response to trigger
            if fuzzyMatchString(trigger, newTrigger)[0]:
                lines[i] = lines[i].strip()
                lines[i] += SPLIT_CHAR + newResponse + '\n'
                triggerMatch = True

        if triggerMatch:
            with open(responseFile, 'w') as responses:
                responses.write(''.join(lines))
                print("Added response to existing trigger \"" + newTrigger + "\"")
        else:  # if the trigger was not in the file before, make a new trigger+response
            with open(responseFile, 'a') as responses:
                responses.write('\n' + newTrigger + SPLIT_CHAR + newResponse)
                print("Added new trigger/response \"" + newTrigger + "\"/\"" + newResponse + "\"")

    async def getResponse(responseFile, message):
        # get trigger
        triggerList = str(message.content).split()[1:]
        trigger = ""
        for word in triggerList:
            trigger += word + ' '
        trigger = sanitize_string(trigger)

        # open file of responses
        with open(responseFile, 'r') as responseFile:
            lines = responseFile.readlines()

        # iterate for the number of words in the trigger
        for i in range(len(trigger.split())):
            for line in lines:
                entries = line.split(SPLIT_CHAR)
                lineTrigger = entries[0]

                # add new response to trigger
                if fuzzyMatchString(trigger, lineTrigger)[0]:
                    responses = entries[1:]
                    response = random.choice(responses)
                    return response

        return STR_NO_RESPONSE

    # match strings with fuzzywuzzy
    def fuzzyMatchString(str1, str2):
        partialRatio = fuzz.partial_ratio(str1, str2)
        tokenSetRatio = fuzz.token_set_ratio(str1, str2)
        tokenSortRatio = fuzz.token_sort_ratio(str1, str2)
        ratio = fuzz.ratio(str1, str2)
        partialTokenSetRatio = fuzz.partial_token_set_ratio(str1, str2)
        partialTokenSortRatio = fuzz.partial_token_sort_ratio(str1, str2)

        scores = [ratio, partialRatio, tokenSetRatio, tokenSortRatio]
        weights = (1.2, 0.8, 1.1, 1)

        sumScores = 0
        for i in range(len(scores)):
            sumScores += (scores[i] / 100) * weights[i]

        probability = sumScores / len(scores)

        isMatch = False
        if probability > PROB_MIN:
            isMatch = True

        print("Analysis of \"", str1, "\" with \"", str2, "\" \n",
              "Matched? ", isMatch, "\n",
              "Partial ratio: ", partialRatio, "\n",
              "Ratio: ", ratio, "\n",
              "Token set ratio: ", tokenSetRatio, "\n",
              "Token sort ratio: ", tokenSortRatio, "\n",
              "Partial token set ratio: ", partialTokenSetRatio, "\n",
              "Partial token sort ratio: ", partialTokenSortRatio, "\n",
              "Probability: ", probability)

        return isMatch, partialRatio, ratio  # return tuple of values
