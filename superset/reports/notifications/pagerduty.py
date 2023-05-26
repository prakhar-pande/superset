import json
import logging
import re
from io import IOBase
from typing import List, Sequence, Union

import requests

from superset import app
from superset.reports.models import ReportRecipientType
from superset.reports.notifications.base import BaseNotification
from superset.reports.notifications.exceptions import (
    NotificationAuthorizationException,
    NotificationMalformedException,
    NotificationParamException,
    NotificationUnprocessableException,
)
from superset.utils.decorators import statsd_gauge

logger = logging.getLogger(__name__)


class PagerDutyNotification(BaseNotification):  # pylint: disable=too-few-public-methods
    """
    Creates a PagerDuty Incident for the Given team
    """

    type = ReportRecipientType.PAGERDUTY

    def _get_payload_info(self) -> List[str]:
        address_string: str = json.loads(self._recipient.recipient_config_json)[
            "target"
        ]
        address_string_list: List[str] = []
        if isinstance(address_string, str):
            address_string_list = re.split(r",|\s|;", address_string)
        return [x.strip() for x in address_string_list if x.strip()]

    def _get_pagerduty_payload(self) -> json:
        try:
            payload: json = json.dumps(
                {
                    "payload": {
                        "summary": "CRITICAL - PROD - Data-Platform - NRT - ",
                        "source": "AppInternalAlert",
                        "severity": "critical",
                        "group": "nrt",
                        "class": "ModelFailure",
                        "component": "prism-model",
                        "custom_details": {
                            "alarm_name": "Failure",
                            "description": "description",
                            "meesho_env": "prod",
                            "meesho_bu": "nrt-platform",
                            "meesho_pod": "data-platform",
                            "meesho_team": "nrt",
                            "meesho_metric": "meesho_metric",
                            "meesho_value": "meesho_value",
                            "meesho_app": "prism-model",
                        },
                    },
                    "routing_key": app.config["PAGERDUTY_ROUTING_KEY_BIZFIN"],
                    "dedup_key": "severity=critical,env=prod,bu=dp,pod=shared,team=bizops,service=NRT",
                    "images": [
                        {
                            "src": "https://www.pagerduty.com/wp-content/uploads/2016/05/pagerduty-logo-green.png",
                            "href": "https://example.com/",
                            "alt": "Example text",
                        }
                    ],
                    "links": [{"href": "https://example.com/", "text": "Link text"}],
                    "event_action": "trigger",
                    "client": "Superset",
                    "client_url": "https://di-prd-superset.meesho.com",
                }
            )
            return payload
        except Exception as e:
            logger.error("Error while creating the payload for pager_duty")
            logger.error(e)
            return False

    @statsd_gauge("reports.pagerduty.send")
    def send(self) -> None:
        user_input: List[str] = self._get_payload_info()
        payload: json = self._get_pagerduty_payload()
        logger.info(payload)
        logger.info(user_input)
        try:
            pager_duty_url = "https://events.pagerduty.com/v2/enqueue"
            res = requests.post(
                pager_duty_url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            logger.info(res.raw)
        except:
            pass
