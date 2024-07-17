import hgtk
from konlpy.tag import Kkma
import torch
from transformers import BertTokenizer, BertModel

kkma = Kkma()

# Example sentence
text = "하늘고에서 맏이하는 아침은 정말 졸리다."

morphs = kkma.morphs(text)
print("Morphemes:", morphs)


# 자모 분리
def decompose_text(text):
    return [hgtk.letter.decompose(char) if hgtk.checker.is_hangul(char) else (char, '', '') for char in text]


# 음절의 끝소리 규칙
def apply_final_consonant_rule(jamos):
    result = []
    for jamo in jamos:
        if jamo[2] in ['ㄲ', 'ㅋ']:
            result.append((jamo[0], jamo[1], 'ㄱ'))
        elif jamo[2] in ['ㅅ', 'ㅆ', 'ㅈ', 'ㅊ', 'ㅌ', 'ㅎ']:
            result.append((jamo[0], jamo[1], 'ㄷ'))
        elif jamo[2] in ['ㅂ', 'ㅍ']:
            result.append((jamo[0], jamo[1], 'ㅂ'))
        else:
            result.append(jamo)
    return result


# 비음화 및 유음화
def apply_consonant_assimilation(jamos):
    assimilated = []
    for i in range(len(jamos) - 1):
        current_char = jamos[i]
        next_char = jamos[i + 1]

        # 비음화
        if current_char[2] in ['ㄱ', 'ㄷ', 'ㅂ'] and next_char[0] == 'ㄴ':
            assimilated.append((current_char[0], current_char[1], 'ㅇ'))
        elif current_char[2] == 'ㄹ' and next_char[0] == 'ㄴ':
            assimilated.append((current_char[0], current_char[1], 'ㄹ'))

        # 유음화
        elif current_char[2] == 'ㄴ' and next_char[0] == 'ㄹ':
            assimilated.append((current_char[0], current_char[1], 'ㄹ'))
        else:
            assimilated.append(current_char)

    assimilated.append(jamos[-1])  # 마지막 자모는 변하지 않음
    return assimilated


# 구개음화
def apply_palatalization(jamos):
    result = []
    for jamo in jamos:
        if jamo[0] == 'ㄷ' and jamo[1] == 'ㅣ':
            result.append(('ㅈ', '', jamo[2]))
        elif jamo[0] == 'ㅌ' and jamo[1] == 'ㅣ':
            result.append(('ㅊ', '', jamo[2]))
        else:
            result.append(jamo)
    return result


# 자음 축약
def apply_consonant_contraction(jamos):
    result = []
    for jamo in jamos:
        if jamo[2] == 'ㅎ':
            if jamo[0] == 'ㄱ':
                result.append(('ㅋ', '', ''))
            elif jamo[0] == 'ㄷ':
                result.append(('ㅌ', '', ''))
            elif jamo[0] == 'ㅂ':
                result.append(('ㅍ', '', ''))
            elif jamo[0] == 'ㅈ':
                result.append(('ㅊ', '', ''))
        else:
            result.append(jamo)
    return result


# 모음 축약
def apply_vowel_contraction(jamos):
    result = []
    for i in range(len(jamos) - 1):
        current_char = jamos[i]
        next_char = jamos[i + 1]

        if current_char[1] == 'ㅣ' and next_char[1] == 'ㅓ':
            result.append((current_char[0], 'ㅕ', next_char[2]))
        elif current_char[1] == 'ㅡ' and next_char[1] == 'ㅣ':
            result.append((current_char[0], 'ㅢ', next_char[2]))
        elif current_char[1] == 'ㅗ' and next_char[1] == 'ㅣ':
            result.append((current_char[0], 'ㅚ', next_char[2]))
        elif current_char[1] == 'ㅗ' and next_char[1] == 'ㅏ':
            result.append((current_char[0], 'ㅘ', next_char[2]))
        elif current_char[1] == 'ㅜ' and next_char[1] == 'ㅓ':
            result.append((current_char[0], 'ㅝ', next_char[2]))
        elif current_char[1] == 'ㅚ' and next_char[1] == 'ㅓ':
            result.append((current_char[0], 'ㅙ', next_char[2]))
        else:
            result.append(current_char)

    result.append(jamos[-1])
    return result


# 된소리되기 규칙
def apply_fortis(jamos):
    result = []
    for i in range(len(jamos) - 1):
        current_char = jamos[i]
        next_char = jamos[i + 1]

        if current_char[2] in ['ㄱ', 'ㄷ', 'ㅂ'] and next_char[0] in ['ㄱ', 'ㄷ', 'ㅂ', 'ㅅ', 'ㅈ']:
            if next_char[0] == 'ㄱ':
                result.append((current_char[0], current_char[1], 'ㄲ'))
            elif next_char[0] == 'ㄷ':
                result.append((current_char[0], current_char[1], 'ㄸ'))
            elif next_char[0] == 'ㅂ':
                result.append((current_char[0], current_char[1], 'ㅃ'))
            elif next_char[0] == 'ㅅ':
                result.append((current_char[0], current_char[1], 'ㅆ'))
            elif next_char[0] == 'ㅈ':
                result.append((current_char[0], current_char[1], 'ㅉ'))
        else:
            result.append(current_char)

    result.append(jamos[-1])
    return result


# 사잇소리 규칙
def apply_linked_sound_rule(jamos):
    result = []
    for i in range(len(jamos) - 1):
        current_char = jamos[i]
        next_char = jamos[i + 1]

        if current_char[2] and hgtk.checker.is_hangul(next_char[0]):
            if hgtk.letter.compose(current_char[0], current_char[1], current_char[2]) in ['등', '손', '김', '밤', '산']:
                result.append(current_char)
                result.append(('ㄸ', next_char[1], next_char[2]))
            else:
                result.append(current_char)
        else:
            result.append(current_char)

    result.append(jamos[-1])
    return result


# 음운 변동 적용
def apply_phonological_rules(morph):
    jamos = decompose_text(morph)
    jamos = apply_final_consonant_rule(jamos)
    jamos = apply_consonant_assimilation(jamos)
    jamos = apply_palatalization(jamos)
    jamos = apply_consonant_contraction(jamos)
    jamos = apply_vowel_contraction(jamos)
    jamos = apply_fortis(jamos)
    jamos = apply_linked_sound_rule(jamos)
    return jamos


# 음운론 추가 기능 구현
class PhonemeAnalyzer:
    def __init__(self):
        self.consonants = {
            'bilabial': ['ㅂ', 'ㅃ', 'ㅍ', 'ㅁ'],
            'labiodental': [],
            'dental': [],
            'alveolar': ['ㄴ', 'ㄷ', 'ㄸ', 'ㅌ', 'ㄹ'],
            'palatal': ['ㅈ', 'ㅉ', 'ㅊ'],
            'velar': ['ㄱ', 'ㄲ', 'ㅋ'],
            'glottal': ['ㅎ']
        }

        self.manner_of_articulation = {
            'plosive': ['ㅂ', 'ㅃ', 'ㅍ', 'ㄷ', 'ㄸ', 'ㅌ', 'ㄱ', 'ㄲ', 'ㅋ'],
            'affricate': ['ㅈ', 'ㅉ', 'ㅊ'],
            'fricative': ['ㅅ', 'ㅆ', 'ㅎ'],
            'nasal': ['ㅁ', 'ㄴ', 'ㅇ'],
            'liquid': ['ㄹ']
        }

        self.vowels = {
            'height': {
                'high': ['ㅣ', 'ㅟ', 'ㅜ', 'ㅡ'],
                'mid': ['ㅔ', 'ㅚ', 'ㅗ', 'ㅓ', 'ㅐ'],
                'low': ['ㅏ']
            },
            'front_back': {
                'front': ['ㅣ', 'ㅔ', 'ㅐ'],
                'back': ['ㅜ', 'ㅗ', 'ㅚ', 'ㅡ', 'ㅓ']
            },
            'rounding': {
                'round': ['ㅟ', 'ㅚ', 'ㅗ', 'ㅜ'],
                'unround': ['ㅏ', 'ㅓ', 'ㅐ', 'ㅔ', 'ㅣ', 'ㅡ']
            }
        }

        self.allophone_rules = {
            'ㅂ': {'initial': 'p', 'medial': 'b', 'final': 'p̚'},
            'ㄹ': {'initial': 'r', 'medial': 'l'}
        }

        self.constraints = {
            'initial': ['ㄴ', 'ㄹ', 'ㅁ', 'ㅇ', 'ㄷ', 'ㅂ', 'ㅅ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'],
            'medial': ['ㄴ', 'ㄹ', 'ㅁ', 'ㅇ', 'ㄷ', 'ㅂ', 'ㅅ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'],
            'final': ['ㄱ', 'ㄴ', 'ㄷ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅇ']
        }

        self.complex_final_consonants = {
            'ㄳ': 'ㄱ', 'ㄵ': 'ㄴ', 'ㄼ': 'ㄹ', 'ㄽ': 'ㄹ', 'ㅄ': 'ㅂ',
            'ㄺ': 'ㄱ', 'ㄻ': 'ㅁ', 'ㄿ': 'ㅂ'
        }

    def classify_consonant(self, consonant):
        features = []
        for key, value in self.consonants.items():
            if consonant in value:
                features.append(key)
        for key, value in self.manner_of_articulation.items():
            if consonant in value:
                features.append(key)
        return features

    def classify_vowel(self, vowel):
        features = []
        for key, value in self.vowels['height'].items():
            if vowel in value:
                features.append(f'{key}모음')
        for key, value in self.vowels['front_back'].items():
            if vowel in value:
                features.append(f'{key}설모음')
        for key, value in self.vowels['rounding'].items():
            if vowel in value:
                features.append(f'{key}순모음')
        return features

    def phoneme_distinction(self, phoneme1, phoneme2):
        if phoneme1 != phoneme2:
            return '변별적'
        else:
            return '비변별적'

    def allophones(self, phoneme, context):
        if phoneme in self.allophone_rules:
            return self.allophone_rules[phoneme].get(context, phoneme)
        return phoneme

    def distribution_constraints(self, phoneme, position):
        if phoneme in self.constraints[position]:
            return True
        return False

    def simplify_final_consonant(self, complex_final):
        return self.complex_final_consonants.get(complex_final, complex_final)


analyzer = PhonemeAnalyzer()

jamo_list = [decompose_text(morph) for morph in morphs]
print("\nDecomposed Jamos:")
for morph, jamos in zip(morphs, jamo_list):
    print(f"Morpheme: {morph}, Jamos: {jamos}")

# 음운 변동 적용
phonological_analysis = [apply_phonological_rules(morph) for morph in morphs]
print("\nPhonological Analysis:")
for morph, jamos in zip(morphs, phonological_analysis):
    print(f"Morpheme: {morph}, Phonological Jamos: {jamos}")

# 자음
consonants = ['ㅂ', 'ㄷ', 'ㄹ', 'ㅈ']
for consonant in consonants:
    print(f"Consonant: {consonant}, Features: {analyzer.classify_consonant(consonant)}")

# 모음
vowels = ['ㅣ', 'ㅏ', 'ㅜ', 'ㅔ']
for vowel in vowels:
    print(f"Vowel: {vowel}, Features: {analyzer.classify_vowel(vowel)}")

# 음소 변별
phoneme_pairs = [('ㅁ', 'ㅂ'), ('ㅂ', 'ㅃ'), ('ㄹ', 'ㄴ')]
for p1, p2 in phoneme_pairs:
    print(f"Phoneme Distinction between {p1} and {p2}: {analyzer.phoneme_distinction(p1, p2)}")

# 이음
phonemes = ['ㅂ', 'ㄹ']
for phoneme in phonemes:
    print(
        f"Allophones of {phoneme}: Initial: {analyzer.allophones(phoneme, 'initial')}, Medial: {analyzer.allophones(phoneme, 'medial')}, Final: {analyzer.allophones(phoneme, 'final')}")

# 분포 제약
distribution_tests = [('ㄴ', 'initial'), ('ㄱ', 'final'), ('ㅎ', 'medial')]
for phoneme, position in distribution_tests:
    print(
        f"Distribution constraint for {phoneme} in {position} position: {analyzer.distribution_constraints(phoneme, position)}")

# 받침 단순화
complex_finals = ['ㄳ', 'ㄵ', 'ㄼ']
for complex_final in complex_finals:
    print(f"Simplified final consonant for {complex_final}: {analyzer.simplify_final_consonant(complex_final)}")
