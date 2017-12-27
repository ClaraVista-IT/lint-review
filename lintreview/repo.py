from __future__ import absolute_import
from json import dumps
import lintreview.github as github
import logging

log = logging.getLogger(__name__)


class GithubRepository(object):
    """Abstracting wrapper for the
    various interactions we have with github.

    This will make swapping in other hosting systems
    a tiny bit easier in the future.
    """
    repo = None

    def __init__(self, config, user, repo_name):
        self.config = config
        self.user = user
        self.repo_name = repo_name

    def repository(self):
        """Get the underlying repository model
        """
        if not self.repo:
            self.repo = github.get_repository(
                self.config,
                self.user,
                self.repo_name)
        return self.repo

    def pull_request(self, number):
        """Get a pull request by number.
        """
        pull = self.repository().pull_request(number)
        return GithubPullRequest(pull)

    def ensure_label(self, label):
        """Create label if it doesn't exist yet
        """
        repo = self.repository()
        if not repo.label(label):
            repo.create_label(
                name=label,
                color="bfe5bf",  # a nice light green
            )

    def create_status(self, sha, state, description):
        """Create a commit status
        """
        context = self.config.get('APP_NAME', 'lintreview')
        repo = self.repository()
        repo.create_status(
            sha,
            state,
            None,
            description,
            context)

    def create_blob(self, *args, **kwargs):
        """Create a blob object
        """
        return self.repository().create_blob(*args, **kwargs)

    def create_tree(self, *args, **kwargs):
        """Create a tree object
        """
        log.info('Creating new tree object')
        return self.repository().create_tree(*args, **kwargs)

    def create_commit(self, *args, **kwargs):
        """Create a commit object
        """
        log.info('Creating commit for tree %s', kwargs['tree'])
        return self.repository().create_commit(*args, **kwargs)

    def update_branch(self, branch, sha):
        """Update a branch

        There is no github3 wrapper API for this.
        """
        log.info('Updating %s to %s', branch, sha)

        repo = self.repository()
        ref = u"heads/{}".format(branch)
        url = repo._build_url('git', 'refs', ref, base_url=repo._api)
        data = {'sha': sha}
        return repo._json(repo._patch(url, data=dumps(data)), 201)


class GithubPullRequest(object):
    """Abstract the underlying github models.
    This makes other code simpler, and enables
    the ability to add other hosting services later.
    """

    def __init__(self, pull_request):
        self.pull = pull_request

    @property
    def display_name(self):
        data = self.pull.as_dict()
        return u'%s#%s' % (data['head']['repo']['full_name'],
                           data['number'])

    @property
    def number(self):
        return self.pull.number

    @property
    def is_private(self):
        data = self.pull.as_dict()
        return data['head']['repo']['private']

    @property
    def head(self):
        data = self.pull.as_dict()
        return data['head']['sha']

    @property
    def clone_url(self):
        data = self.pull.as_dict()
        return data['head']['repo']['clone_url']

    @property
    def base_repo_url(self):
        data = self.pull.as_dict()
        return data['base']['repo']['clone_url']

    @property
    def target_branch(self):
        data = self.pull.as_dict()
        return data['base']['ref']

    @property
    def head_branch(self):
        data = self.pull.as_dict()
        return data['head']['ref']

    def head_repository(self, app_config):
        """Get a GithubRepository for the head side of the pull request.
        """
        data = self.pull.as_dict()
        return GithubRepository(
            app_config,
            data['head']['repo']['owner']['login'],
            data['head']['repo']['name'])

    def commits(self):
        return self.pull.commits()

    def review_comments(self):
        return self.pull.review_comments()

    def files(self):
        return list(self.pull.files())

    def remove_label(self, label_name):
        issue = self.pull.issue()
        labels = issue.labels()
        if not any(label_name == label.name for label in labels):
            return
        log.debug("Removing issue label '%s'", label_name)
        issue.remove_label(label_name)

    def add_label(self, label_name):
        issue = self.pull.issue()
        issue.add_labels(label_name)

    def create_comment(self, body):
        self.pull.create_comment(body)

    def create_review(self, review):
        url = self.pull._build_url('reviews', base_url=self.pull._api)
        self.pull._json(self.pull._post(url, data=review), 201)

    def create_review_comment(self, body, commit_id, path, position):
        self.pull.create_review_comment(body, commit_id, path, position)
