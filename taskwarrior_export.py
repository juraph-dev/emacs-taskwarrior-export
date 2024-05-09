#!/usr/bin/python
import re
import code
import argparse
import subprocess

from datetime import datetime, timedelta
from taskw_ng import TaskWarrior, exceptions

client = TaskWarrior()

priority_table = {'A' : 'H', 'B' : 'M' , 'C' : 'L'}
priority_pattern = re.compile(r'(?s:\[\#.\])')

org_matches = ["TODO", "DONE", "STRT"]
schedule_matches = ["SCHEDULED: ", "DEADLINE: "]


def flatten(d):
  '''Flatten.'''
  for i in d:
     yield from [i] if not isinstance(i, tuple) else flatten(i)


def parse_scheduled_string(date_string):
    '''Parser for ORG schedules, of form SCHEDULED: <2024-05-06 Mon 14:00-16:00 +1w>'''
    # Remove the angle brackets from the string
    date_string = date_string.strip("<>")
    # Handle date ranges with recursion baby!
    if "--" in date_string:
        start_date_string, end_date_string = date_string.split("--")
        start_datetime_obj = parse_scheduled_string(f"<{start_date_string}>")
        end_datetime_obj = parse_scheduled_string(f"<{end_date_string}>")
        return start_datetime_obj, end_datetime_obj

    # Check if the end_date_string contains a repeat modifier (e.g., +1w)
    if "+" in date_string:
        date_string, repeat_time =  date_string.split('+')
        repeat_count, repeat_unit = int(repeat_time[0]), repeat_time[1]
        if repeat_unit == "w":
            repeat_delta = repeat_time[0] + "week"
        elif repeat_unit == "d":
            repeat_delta = repeat_time[0] + "day"
        else:
            raise ValueError("Invalid repeat modifier")
        return parse_scheduled_string(f"<{date_string[:-1]}>"), repeat_delta
    # Attempt to parse timestamp with hours/minutes
    try:
        return datetime.strptime(date_string, "%Y-%m-%d %a %H:%M")
    except ValueError:
        # If the first format fails, try parsing as YMD
        try:
            return datetime.strptime(date_string, "%Y-%m-%d %a")
        except ValueError:
            # MAYBE we are parsing an item with a duration.
            try:
                date_string, _, duration = date_string.rpartition('-')
                end_time = date_string[:-len(duration)] + duration
                start_datetime = parse_scheduled_string(f"<{date_string[:-1]}>")
                end_datetime = parse_scheduled_string(f"<{end_time}>")
                return start_datetime, end_datetime - start_datetime
                # If both formats fail, fucken panic lmao.
            except:
                raise ValueError("Invalid date string format")
    return datetime_obj

def parse_datetime(task_datetime):
    if not type(task_datetime) == list:
        return task_datetime, None, None
    # Check type of second entry in list.
    if (type(task_datetime[1]) == datetime):
        delta = task_datetime[1] - task_datetime[0]
        return task_datetime[0], delta, None
    # Check for a timedelta of seconds, which will indicate a task with a duration. Such as a meeting
    if (type(task_datetime[1]) != str):
        # if task is simply start date & duration
        if (len(task_datetime) == 2):
            return task_datetime[0], task_datetime[1], None

    # If we have made it this far, with a length of two, most likely
    # have task of form [date - Repeat]
    if (len(task_datetime) == 2):
        return task_datetime[0], None, task_datetime[1]

    # Final case - most likely have form [date - duration - repeat]
    return task_datetime[0], task_datetime[1], task_datetime[2]

def parse_org_mode_tasks(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    split_file = content.split('\n')
    tasks = []
    for idx, line in enumerate(split_file):
        priority = ''
        # A task can have priorities ([#A], [#B] [#C]). Translate to
        # taskwarrior Low, Medium, High priortiies, Trimmming from
        # string in process
        if priority_pattern.search(line):
            leading_bracket = line.find("[#")
            priority = priority_table[line[leading_bracket+2]]
            line = line[:leading_bracket] + line[line.find("]") + 2:]
        # Ensure task has a marker of TODO, DONE etrc before adding it to task list.
        # We store the state as we use this to determine if we should mark an existing
        # taskwarrior task as comeplete
        if any(map(line.__contains__, org_matches)):
            state = next(substring for substring in org_matches if substring in line)
            task = line[line.find(str( state ))+5:]
            start = duration = repeat = None
            # Check next index for a SCHEDULED property
            if any(map(split_file[idx+1].__contains__, schedule_matches)):
                schedule_type = next(substring for substring in schedule_matches if substring in split_file[idx+1])
                task_deadline = split_file[idx+1].split(schedule_type)[1]
                # Parse the string into a datetime object
                task_datetime = parse_scheduled_string(task_deadline)
                if (type(task_datetime) == tuple):
                    task_datetime = list(flatten(task_datetime))
                start, duration, repeat = parse_datetime(task_datetime)
            tasks.append((task, priority, state, start, duration, repeat))
    return tasks

def get_task_object(task_desc):
    '''Getter function. Mostly used to prevent failures when task string has unexpected characters'''
    try:
        return client.get_task(description=task_desc)
    except exceptions.TaskwarriorError as error:
        print(f'Failed to import task {task_desc}: ', error)
        return None, -1

def import_tasks_to_taskwarrior(tasks):
    current_list = client.load_tasks()
    for task, task_priority, state, start, delta, repeat in tasks:
        task_id, task_object = get_task_object(task)
        if task_object == -1:
            continue
        if task_id is not None:
            if state == "DONE":
                task_object['status'] = 'completed'
                client.task_update(task_object)
            elif state == "STRT":
                task_object['status'] = 'active'
                client.task_update(task_object)
        elif state == "TODO":
            if (start is not None and delta is not None):
                delta = start + delta
            client.task_add(task, priority = task_priority, due=start, until=delta, recur=repeat)

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Export ORG to taskwarrior files")
    parser.add_argument("location", help="Location of Org file to read from", type=str)
    args = parser.parse_args()
    tasks = parse_org_mode_tasks(args.location)
    import_tasks_to_taskwarrior(tasks)
