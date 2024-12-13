CREATE TABLE `wiki_articles` (
  `article_id` bigint(19) unsigned NOT NULL AUTO_INCREMENT,
  `title` varchar(255),
  `summary` text,
  `image_url` text,
  PRIMARY KEY (`article_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
