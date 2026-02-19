from pathlib import Path

DIR = Path(__file__).resolve().parent


## 0. define groups
## 1. substitute presubstitution rules
## 2. map letters to IPA
## 3. apply POST sound changes 
def expand_string(pattern, groups, verbose=False):
    """Recursively expand a pattern string into all possible concrete strings."""
    if not pattern:
        return ['']
    
    # Check if first character is a group name
    first_char = pattern[0]
    rest = pattern[1:]
    
    if first_char.isupper() and first_char in groups:
        # Expand the group and recursively expand the rest
        group_items = groups[first_char]
        rest_expansions = expand_string(rest, groups, verbose=verbose)
        
        result = []
        for item in group_items:
            for rest_exp in rest_expansions:
                result.append(item + rest_exp)
        if verbose:
            print(f"Expanding group {first_char}: {group_items} -> {result}")
        return result
    else:
        # Regular character, just append to all expansions of the rest
        rest_expansions = expand_string(rest, groups, verbose=verbose)
        if verbose:
            print(f"Expanding character {first_char}: {rest_expansions}")
        return [first_char + exp for exp in rest_expansions]

def apply_ruleset_bulk(ruleset_content, input_words, verbose_expansion=False, verbose_rules=False):
    ruleset = {}
    current_section = None
    for line in ruleset_content.split("\n"):
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        if line.startswith("$"):
            current_section = line[1:]
            continue
        r = line.split(":")
        if current_section not in ruleset:
            ruleset[current_section] = []
        ruleset[current_section].append(r)



    ## GROUP
    groups = {}
    if "GROUP" in ruleset:
        for group in ruleset["GROUP"]:
            groups[group[0]] = group[1].split(',')
            if verbose_rules:
                print(f"Defined group {group[0]}: {groups[group[0]]}")
    
    ## TODO: pre-substitution rules ?
    
    ## SUBSTITUTION
    if "SUBST" in ruleset:
        for substitution in ruleset["SUBST"]:
            for i, word in enumerate(input_words):
                input_words[i] = word.replace(substitution[0], substitution[1])
    
    ## POST RULES
    if "POST" in ruleset:
        for post_rule in ruleset["POST"]:
            P1 = post_rule[0]
            P2 = post_rule[1]
            if len(post_rule) > 2:
                context = post_rule[2]
                if len(post_rule) > 3:
                    exceptions = post_rule[3]
                else:
                    exceptions = None
            else:
                context = None
                exceptions = None
            if verbose_rules:
                print(f"Applying post rule: {P1} -> {P2} in context {context} with exceptions {exceptions}")

            ## TODO: word boundary context %
            ## TODO: implement exceptions

            S1 = expand_string(P1, groups, verbose=verbose_expansion)
            S2 = expand_string(P2, groups, verbose=verbose_expansion)
            C = expand_string(context, groups, verbose=verbose_expansion) if context else None
            
            if C:
                SS1 = []
                SS2 = []
                for c in C:
                    if '_' not in c:
                        # print(f"ERROR in {post_rule}: Context pattern must include an underscore: {c}")
                        raise ValueError(f"Context pattern must include an underscore: {c}")
                        
                    left, right = c.split('_')
                    SS1.extend([left + s + right for s in S1])
                    SS2.extend([left + s + right for s in S2])
                S1 = SS1
                S2 = SS2

            if len(S1) != len(S2):
                # print(f"ERROR in {post_rule}: Expanded patterns have different lengths: {len(S1)} vs {len(S2)}")
                raise ValueError(f"Expanded patterns have different lengths: {len(S1)} vs {len(S2)}")
                

            if verbose_rules:
                for i, (s1, s2) in enumerate(zip(S1, S2)):
                    print(f"  Rule {i}: {s1} -> {s2}")

            for s1, s2 in zip(S1, S2):
                for i, word in enumerate(input_words):
                    word = '%' + word + '%' # for word boundary context
                    word = word.replace(s1, s2)
                    input_words[i] = word[1:-1]
        

    return input_words

def apply_ruleset(ruleset_content, word, verbose_expansion=False, verbose_rules=False):
    return apply_ruleset_bulk(ruleset_content, [word], verbose_expansion=verbose_expansion, verbose_rules=verbose_rules)[0]


# ruleset_path = DIR / "ruleset.txt"
# input_path = DIR / "input.txt"
# with open(ruleset_path, "r") as f:
#     ruleset_content = f.read()
# input_words = []
# with open(input_path, "r") as f:
#     for line in f:
#         line = line.strip()
#         if line:
#             input_words.append(line)
# print(apply_ruleset_bulk(ruleset_content, input_words, verbose_rules=True))
