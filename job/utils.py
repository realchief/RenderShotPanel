import re
import itertools


def validate_frame_list(items):
    range_pattern_string = r"^(\d+)-{1}(\d+):?(\d+)?"
    single_pattern_string = r"^(\d+)$"

    range_pattern = re.compile(range_pattern_string)
    single_pattern = re.compile(single_pattern_string)

    for item in items:

        single_result = single_pattern.findall(item)
        if single_result:
            return True

        range_result = range_pattern.findall(item)
        if range_result:
            return True

    return "No valid frame list format found."


def validate_file_name(name):
    import string

    for letter in name:
        if letter not in string.printable:
            return f"One or more non-english characters found in the file name."

    bad_chars_string = r'[#%:£¬?\\/"<>|]+'
    bad_chars_pattern = re.compile(r'[#%:£¬?\\/"<>|]+')
    if bad_chars_pattern.findall(name):
        return f"One or more of the following characters found in the file name : {bad_chars_string}"

    return True


def list_to_range(sequence):
    sequence = eval(sequence)

    def make_ranges(sequence_list):
        for a, b in itertools.groupby(enumerate(sequence_list), lambda pair: pair[1] - pair[0]):
            b = list(b)
            yield b[0][1], b[-1][1]

    try:
        result = list(make_ranges(sequence))
        if not result:
            return
        if len(result) == 1:
            return f"{result[0][0]}-{result[0][1]}"

        ranges = []
        for item in result:
            first, last = item
            if not first or not last:
                continue

            if first == last:
                ranges.append(str(first))
                continue

            ranges.append(f"{first}-{last}")

        if not ranges:
            return

        return ",".join(ranges)
    except Exception as err:
        print(err)


def get_job_schema():
    system_info = {
        'plugin_name': '',
        'plugin_version': '',
        'render_plan': '',
        'username': '',
        'storage_type': '',
    }

    job_info = {
        'job_name': '',
        'job_type': '',
        'pool': '',
        'group': '',
        'frame_list': '',
    }

    plugin_info = {
        'image_width': '',
        'image_height': '',
        'quality_mode': '',
        'max_samples': '',
        'custom_samples': '',
        'ray_bounces': '',
        'anti_aliasing_quality': '',
        'shadow_quality': '',
        'educational': '',
        'cameras': '',
    }

    file_info = {
        'file_name': '',
        'relative_url': '',
        'absolute_url': '',
    }

    job_schema = dict()
    job_schema['system_info'] = system_info
    job_schema['job_info'] = job_info
    job_schema['plugin_info'] = plugin_info
    job_schema['file_info'] = file_info

    return job_schema
