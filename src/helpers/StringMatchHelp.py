import re
from enum import Enum, auto
from fuzzywuzzy import fuzz

DEF_WEIGHTS = [1.2, 0.7, 1.1, 1]
DEF_PROB = 0.7


class Output(Enum):
    isMatch = auto
    probability = auto
    scores = auto
    output = auto


def sanitize_string(input, regex=r'[^a-zA-Z ]'):
    return re.sub(regex, '', str(input).strip().lower())


# match strings with fuzzywuzzy
def fuzzyMatchString(str1, str2, weights=DEF_WEIGHTS, probMin=DEF_PROB):
    """
    :param "first string": First string
    :param "second string": Second string
    :param weights: Weights (optional)
    :param "sensitivity (0-1)": Sensitivity (0-1)
    :return:
    """
    output = None

    partialRatio = fuzz.partial_ratio(str1, str2)
    tokenSetRatio = fuzz.token_set_ratio(str1, str2)
    tokenSortRatio = fuzz.token_sort_ratio(str1, str2)
    ratio = fuzz.ratio(str1, str2)
    # partialTokenSetRatio = fuzz.partial_token_set_ratio(str1, str2)
    # partialTokenSortRatio = fuzz.partial_token_sort_ratio(str1, str2)

    scores = [ratio, partialRatio, tokenSetRatio, tokenSortRatio]

    probability = sum([(scores[i]/100.0)*weights[i] for i in range(len(weights))])/sum(weights)

    isMatch = False
    if probability > probMin:
        isMatch = True

        output = "Analysis of \"", str(str1), "\" with \"", str(str2), "\" \n", \
                 "Matched? ", str(isMatch), "\n", \
                 "Partial ratio: ", str(partialRatio), "\n", \
                 "Ratio: ", str(ratio), "\n", \
                 "Token set ratio: ", str(tokenSetRatio), "\n", \
                 "Token sort ratio: ", str(tokenSortRatio), "\n", \
                 "Probability: ", str(probability)

    return isMatch, probability, scores, output  # return matching status and individual scores
