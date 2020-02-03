from grid.deploy import BaseDeployment
from grid import utils as gr_utils

import sys
import os


class HerokuNodeDeployment(BaseDeployment):
    """ An abstraction of heroku grid node deployment process, the purpose of this class is set all configuration needed to deploy grid node application in heroku platform."""

    def __init__(
        self,
        grid_name: str,
        verbose=True,
        check_deps=True,
        app_type: str = "websocket",
        dev_user: str = "OpenMined",
        branch: set = "dev",
        env_vars={},
    ):
        """ Initialize Settings to deploy Grid Node Deployment on Heroku
        Args:
            grid_name: App name used in heroku application.
            verbose: Used to define level of verbosity.
            check_deps: Flag to choose if dependencies will be checked.
            app_type: choose different node app types to deploy (websocket, pg_rest_api, rest_api).
            dev_used: Choose an specific Grid repository (standard: OpenMined repositoy).
            branch: Choose an specific Grid branch (standard: dev branch).
            env_vars: Environment vars used to configure component.
        """
        self.app_type = app_type
        self.grid_name = grid_name
        self.check_deps = check_deps
        self.dev_user = dev_user
        self.branch = branch

        super().__init__(env_vars, verbose)

    def deploy(self):
        """ Method to deploy Grid Node app on heroku platform. """
        if self.grid_name == None:
            raise RuntimeError("Grid name was not specified!")

        app_addr = "https://" + str(self.grid_name) + ".herokuapp.com"

        if self.check_deps:
            self.__check_heroku_dependencies()

        if self.verbose:
            print(
                "\nStep 1: Making sure app name '" + self.grid_name + "' is available"
            )
        try:
            output = list(self._execute(("heroku create " + self.grid_name).split(" ")))
            if self.verbose:
                print("\t" + str(output))
        except:
            if os.name != "nt":
                output = list(self._execute(("rm -rf tmp").split(" ")))
                if self.verbose:
                    print("\t" + str(output))
            print("APP EXISTS: You can already connect to your app at " + app_addr)
            return app_addr

        if self.verbose:
            print("\nStep 3: Cleaning up heroku/postgres checks...")

        output = list(
            self._execute(
                (
                    "heroku destroy " + self.grid_name + " --confirm " + self.grid_name
                ).split(" ")
            )
        )

        self.__run_heroku_commands()
        print("SUCCESS: You can now connect to your app at " + app_addr)

        return app_addr

    def __run_heroku_commands(self):
        """ Add a set of commands/logs used to deploy grid node app on heroku platform. """
        self.logs.append("\nStep 4: cleaning up git")
        self.commands.append("rm -rf .git")

        self.logs.append("Step 5: cloning heroku app code from Github")
        self.commands.append(
            "git clone -b {} https://github.com/{}/PyGrid".format(
                self.branch, self.dev_user
            )
        )

        self.logs.append("Step 6: copying app code from cloned repo")
        self.commands.append("cp -r PyGrid/app/{}/* ./".format(self.app_type))

        self.logs.append("Step 7: removing the rest of the cloned code")
        self.commands.append("rm -rf PyGrid")

        self.logs.append("Step 8: Initializing new github (for Heroku)")
        self.commands.append("git init")

        self.logs.append("Step 9: Adding files to heroku github")
        self.commands.append("git add .")

        self.logs.append("Step 10: Committing files to heroku github")
        self.commands.append('git commit -am "init"')

        self._run_commands_in(
            self.commands, self.logs, cleanup=False, verbose=self.verbose
        )

        self.logs = list()
        self.commands = list()

        self.logs.append(
            "\nStep 11: Pushing code to Heroku (this can take take a few seconds)..."
        )
        self.commands.append("heroku create " + self.grid_name)

        self.logs.append(
            "Step 12: Creating Postgres database... (this can take a few seconds)"
        )
        self.commands.append(
            f"heroku addons:create heroku-postgresql:hobby-dev -a {self.grid_name}"
        )

        for var in self.env_vars:
            self.logs.append("Setting environment variable: ")
            self.commands.append("heroku config:set " + var + "=" + self.env_vars[var])

        self.logs.append(
            "Step 13: Pushing code to Heroku (this can take take a few minutes"
            " - if you're running this in a Jupyter Notebook you can watch progress "
            "in the notebook server terminal)..."
        )
        self.commands.append("git push heroku master")

        self.logs.append("Step 14: Cleaning up!")
        self.commands.append("rm -rf .git")

        self._run_commands_in(
            self.commands, self.logs, cleanup=True, verbose=self.verbose
        )

    def __check_heroku_dependencies(self):
        """ Check specific dependencies to perform grid node deploy on heroku platform. """
        if self.verbose:
            print("Step 0: Checking Dependencies")

        self._check_dependency(
            lib="git",
            check="usage:",
            error_msg="Missing Git command line dependency - please install it: https://gist.github.com/derhuerst/1b15ff4652a867391f03",
            verbose=self.verbose,
        )

        self._check_dependency(
            lib="heroku --version",
            check="heroku/7",
            error_msg="Missing Heroku command line dependency - please install it: https://toolbelt.heroku.com/",
            verbose=self.verbose,
        )

        self._check_dependency(
            lib="pip",
            check="\nUsage:   \n  pip <command> [options]",
            error_msg="Missing Pip command line dependency - please install it: https://www.makeuseof.com/tag/install-pip-for-python/",
            verbose=self.verbose,
        )

        if self.verbose:
            sys.stdout.write("\tChecking to see if heroku is logged in...")
        res = gr_utils.execute_command("heroku create app")
        if res == "Enter your Heroku credentials:\n":
            raise Exception(
                "You are not logged in to Heroku. Run 'heroku login'"
                " from the command line and follow the instructions. "
                " If you need to create an account. Don't forget to add "
                " your credit card. Even though you can use Grid on the"
                " FREE tier, it won't let you activate a Redis database "
                " without adding your credit card information to your account."
            )
        if self.verbose:
            print("DONE!")
