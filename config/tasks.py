TASKS = {
    "CUSTOMER_SERVICE": {
        "handle_inquiry": "handle_customer_inquiry",
        "technical_solution": "provide_technical_solution",
        "process_request": "process_customer_request"
    }
}

def get_task_name(category, task):
    return TASKS.get(category, {}).get(task, "unknown_task")