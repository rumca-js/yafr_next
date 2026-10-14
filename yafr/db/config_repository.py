"""
Configuration Repository for YAFR.

Manages application-wide settings persisted in the configurationentry table,
such as themes, display styles, alpha transparencies, and storage caps.
"""

import logging
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session
from linkarchivetools.model.definitions import ConfigurationEntry
from yafr.db.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ConfigRepository(BaseRepository[ConfigurationEntry]):
    """
    Data access repository for application configuration entries.
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        super().__init__(session=session)

    def get_config(self) -> ConfigurationEntry:
        """
        Retrieves the primary active ConfigurationEntry record.

        If no configuration row exists, initializes a default entry.

        :return: Active ConfigurationEntry instance
        """
        stmt = select(ConfigurationEntry).order_by(ConfigurationEntry.id.asc()).limit(1)
        config = self.session.execute(stmt).scalar_one_or_none()

        if config is None:
            config = ConfigurationEntry(
                instance_title="YAFR",
                instance_description="Yet Another Feed Reader",
                display_style="style-dark",
                display_type="gallery",
                show_icons=True,
                thumbnails_as_icons=True,
                entries_visit_alpha=0.6,
                entries_dead_alpha=0.4,
                max_number_of_user_search=300,
                max_user_entry_visit_history=5000,
                links_per_page=25,
                sources_per_page=25,
                vote_min=-100,
                vote_max=100,
                initialized=True,
            )
            self.session.add(config)
            self.session.commit()
            logger.info("Initialized default ConfigurationEntry (id=%s)", config.id)

        return config

    def update_config(self, **kwargs) -> ConfigurationEntry:
        """
        Updates fields on the active ConfigurationEntry.

        :param kwargs: Key-value attributes to update
        :return: Updated ConfigurationEntry instance
        """
        config = self.get_config()
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                logger.warning("ConfigurationEntry has no attribute '%s'", key)

        self.session.commit()
        return config

    def get_display_style(self) -> str:
        """
        Returns the active display theme style (e.g., 'style-dark', 'style-light').
        """
        config = self.get_config()
        return config.display_style or "style-dark"

    def get_display_type(self) -> str:
        """
        Returns the active layout card type (e.g., 'gallery', 'standard', 'search-engine').
        """
        config = self.get_config()
        return config.display_type or "gallery"

    def get_alphas(self) -> Tuple[float, float]:
        """
        Returns the configured transparency alphas for visited and dead entries.

        :return: Tuple of (entries_visit_alpha, entries_dead_alpha)
        """
        config = self.get_config()
        visit_alpha = float(
            config.entries_visit_alpha
            if config.entries_visit_alpha is not None
            else 0.6
        )
        dead_alpha = float(
            config.entries_dead_alpha if config.entries_dead_alpha is not None else 0.4
        )
        return visit_alpha, dead_alpha
