import inspect
import logging

from services.api_users_service import ApiUsersService


def delete_user_by_login(user_data: dict):
    user_id = ApiUsersService.find_user_by_login(user_data["login"])
    if user_id is not None:
        ApiUsersService.delete_api_user(user_id)
        logging.info(
            f'Function: {inspect.currentframe().f_code.co_name}, {user_data["login"]} is deleted'
        )
