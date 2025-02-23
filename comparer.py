from difflib import SequenceMatcher

def compare_documents(text1, text2):
    matcher = SequenceMatcher(None, text1, text2)
    differences = [diff for diff in matcher.get_opcodes() if diff[0] != 'equal']
    return differences
