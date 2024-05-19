from typing import Optional

import requests


from thoughtspot_rest_api_v1.tsrestapiv2 import TSRestApiV2


class TSRestApiV2Org(TSRestApiV2):
    def auth_session_login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        remember_me: bool = True,
        bearer_token: Optional[str] = None,
        org_identifier: Optional[str] = None,
    ) -> requests.Session:
        endpoint = "auth/session/login"

        url = self.base_url + endpoint

        if bearer_token is not None:
            response = self.requests_session.post(
                url=url,
                headers={"Authorization": "Bearer {}".format(bearer_token)},
                json={"remember_me": str(remember_me).lower()},
            )
        elif username is not None and password is not None:
            json_post_data = {
                "username": username,
                "password": password,
                "remember_me": str(remember_me).lower(),
            }
            if org_identifier is not None:
                json_post_data["org_identifier"] = org_identifier
            response = self.requests_session.post(url=url, json=json_post_data)
        else:
            raise Exception("If using username/password, must include both")

        # HTTP 204 - success, no content
        response.raise_for_status()
        return self.requests_session
