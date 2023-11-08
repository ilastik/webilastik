"Webilastik" is a rewrite of classic ilastik's architecture to make it more portable and to drop legacy code.

For motivation on the design decisions, have a look at the [presentation](https://docs.google.com/presentation/d/110_1IOqel1QU1aKrznDaZIT5Rr1HbTbUVOfxwVnFFO0/edit?usp=sharing)


Webilastik heavily uses [ndstructs](https://github.com/ilastik/ndstructs) to have sane 5D arrays, points and slices.

# Basics

Have a look at `examples/pixel_classification_basics.py` to see webilastik being used as a synchronous library.

# Concepts

## DataSource

A class that inherits from the base `DataSource` provides tiled image data to be processed. An instance of `DataSource` is aware of the image's size, shape, data type and tile shape.

## DataRoi

A `DataRoi` is a class that encapsulates both a a `DataSource` and an `Interval`, and represents an area of interest on a particular image. Because a `DataRoi` also carries a reference to the `DataSource` itself, it can be moved and/or expanded over the contents of the image, which is useful when dealing with operations than need a halo around a particular region of interest. You can get the actual data pointed to by a `DataRoi` by calling `retrieve()`, which will return an `Array5D`.

## Operators

A refinement of the Operator concept in classic ilastik; they represent a lazy computation that usually can be applied to a `webilastik.datasource.DataRoi`.

Operators implement the `Operator[IN, OUT]` protocol and for now must only implement `def __call__(self, /, input: IN) -> OUT` . The most common implementation being `.__call__(self, /, roi: DataRoi) -> Array5D` when dealing with operators that use halos. This means that once you have an operator instantiated, you can apply it over any slice of any `DataSource` and the operator will be able to retrieve any extra data if needs from the `DataRoi` object.

Operators **do not** deal with "Slots" or "dirty propagation" like in classic ilastik; This functionality is UI-only in webilastik. Operators are always ready to compute and do not need any other steps to be taken beyond successfully constructing one.

Wherever it makes sense, operators will take a `preprocessor: Optional[Operator]` constructor argument, which allows them to be composed with each other, e.g.:

```python
thresholder_op = Thresholder(threshold=30)
connected_components_op = ConnectedComponentsExtractor(
    preprocessor=thresholder_op, ...
)
# the connected components operator will first threshold the data with thresholder_op,
# and then look for the components on the thresholded data
# on the thresholded data
connected_components: Array5D = connected_components_op(roi=some_region_of_the_image)
```

## Applets

`Applets` are a UI-only concept; they usually will represent the user's intent on creating an `Operator`, but they can also just represent the "model" behind some GUI widget like a form.

Applets are organized in a Directed Acyclic Graph, where the vertices are the Applets and the edges are `AppletOutputs` (see section below).

The base `Applet` class contains some `__init__` logic which registers dependencies between applets; It does so by scanning all the applet attributes and keeping track of the ones that are instances of `AppletOutput` (see next session) and that belong to a different applet than `self`. This **must run after all attributes of 'self' have been set** in the child class constructor. The easiest way to achieve that is to make sure custom applets call `super().__init__()` as the **last step** of their construction. This restriction allows for easy inheritance between custom `Applets`, with child classes creating more `AppletOutputs`.

Applets are constructed already connected to all of its upstream applets and cannot disconnect from them throughout their lifetimes. In practice, this means that the `Applet` constructor should take as parameters all the `AppletOutputs` from upstream applets that it might need to perform its task.

### AppletOutputs  - applet "live properties"

Applets declare their observable properties by annotating a method with `@applet_output`. This transforms that method into an object of type `AppletOutput`, which can then be fed downstream to the other applets. You can think of an `AppletOutput` as a bound method where `self` is an `Applet`.

Whenever a constructor from one applet (say, B) takes an `AppletOutput` from another applet (say, A), then B is said to be downstream from A, i.e., changes in applet A will trigger a call to `B.refresh()`, giving B an opportunity to update its values to reflect the changes that happened upstream at A.

### Cascading changes

Whenever an applet defines a method that changes the applet's state, that method should be annotated with the `@cascade` decorator. This decorator will cause downstream applets to be notified that something changed upstream by calling their `refresh` method (which is equivalent in spirit to the `setupOutputs` method in classic ilastik's Operators).

A method decorated with `@cascade` must take a `user_prompt: UserPrompt` parameter. This is a function that can be called by downstream applets to get user confirmation whenever they are about to do something that the user might regret (like destroying data or cause long-running computations to be triggered). If the user does not confirm the action in a way that a downstream applet expects, the entire cascade transaction is aborted and all applets are reverted to their previous state.

## Workflows

Workflows are a predefined collection of `Applets` (and therefore a concept of the UI, not the API). Ideally, workflows would implement no extra logic; As much as possible, the `Applets` should be independant of external logic, so that they can be reused in multiple workflows. Interaction with a workflow should also be through the applets, so in a `PixelClassificationWorkflow`, for example, adding brush strokes is done via the `PixelClassificationWorkflow.brushing_applet : BrushingApplet` attribute, and not through some custom workflow method that would have to be re-implemented for every workflow.

Check out `webilastik/ui/workflow/pixel_classification_workflow.py` of what a typical workflow should look like.

# Server

In order to use ilastik over the web, a user must first allocate a session (which for now can run either locally as a separate process or remotely on CSCS). This session allocation is done by `webilastik/server/session_allocator.py`. This executable is an HTTP handler that will itself spawn other HTTP servers, which are the user sessions, and those sessions will actually run computations for the user.

An HTTP server to expose webilastik should be configured with options analogous to those in `package_tree/etc/nginx/sites-available/webilastik.conf`. The important thing to note is the redirection from requests of the form `session-<session-id>` to `http://unix:/tmp/to-session-$session_id`, since those unix sockets will tunnel back to the user sessions, which might be running in different machines than that which is hosting `webilastik/server/session_allocator.py`. Also, CORS must be enabled since ilastik will probably not be running on the same server as the viewer.

# Client (Overlay)

This project contains an npm project in `./overlay`, which can be used to build the ilastik client. It is an overlay that can be applied on top of neuroglancer and contains all controls required to request a session, add brush strokes, select image features and visualize predictions.

# Building
 - Install build dependencies:
    - [conda-pack](https://conda.github.io/conda-pack/) (for wrapping the conda environment)
    - [go-task](https://taskfile.dev/installation) (make-like application to build the targets in Taskfile.yml)
    - npm (for building neuroglancer and the overlay. using version `6.14.16` at the time of writing)
 - Set up environment variables:
    - `EBRAINS_CLIENT_ID`: the `cliend-id` of the app as defined by the EBRAINS OIDC. Right now it's `webilastik`
    - `EBRAINS_CLIENT_SECRET`: the `client-secret` of the OIDC app, which you have to either retrieve from the OIDC itself or from a human that has it stored somewhere safe. It looks like a uuid.
    - `WEBILASTIK_SESSION_ALLOCATOR_FERNET_KEY`: this is a base64-encoded [Fernet key](https://cryptography.io/en/41.0.4/fernet/) that is used to encrypt data on the HPCs that are not meant to be visible to other users of SLURM
 - Build the `.deb` package: `task create-deb-package`

| :warning: WARNING!                                                                                                         |
|:---------------------------------------------------------------------------------------------------------------------------|
| Do not publish this `.deb` package as an artifact anywhere, as it contains the app secrets from your environment variables |

The resulting `.deb` package is the one installed in the VM at app.ilastik.org. It will contain the web server, the conda environment required to run it, the neuroglancer-based frontend as well as the Systemd `.service` (with all relevant keys) file needed to automatically start the service on boot. Updating the server is just reinstalling the old `.deb` and installing the new one, which will also take care of stopping and restarting the service.

# Deploying to production

## Deploying the web server to app.ilastik.org
- Build the `.deb` package as explained in the `Building` session
- Install the newly created `.deb` package (e.g. `sudo apt install ./webilastik*.deb`)
- Configure SSL if that's the first time you install webilastik on this server (e.g.: `sudo certbot --nginx -d app.ilastik.org`)

This is usually automated via the `deploy` task in the `Taskfile.yml`

## Deploying the code the HPCs
This part has to be done manually for the first time, as each HPC has its own particularities that need to we worked with (or around). This should be more configurable in the future, but right now the source of truth are the job launcher classes in `compute_session_launcher.py`

### JUSUF
- Install `miniconda`
- Run the `./scripts/configure_jusuf.sh` on the HPC only once to configure it
- If you update the `environment.yml` file you will have to destroy the conda env and run the script again
- Simply updating the webilastik source code will be accounted for automatically by the `deploy` target

## Configuring SSH keys
For communication between the web server and the HPC, these steps must be done only once:

- The web server at app.ilastik.org must be able to SSH to the HPCs, to you must install the www-data SSH key in the HPCs
- The HPCs must be able to SSH back to app.ilastik.org to stabilish reverse tunnels, so their keys have to be installed in the allowed keys of of the `www-data` user in `app.ilastik.org`

# Local dev server
Even the local server needs Nginx to be running. This is because webilastik allocates worker sessions for the users, and those sessions can be running in remote worker servers. These worker sessions create SSH tunnels on the main server, and nginx will redirect session requests into those tunnels sockets.

- Install nginx
- Add `webilastik.conf` to nginx configuration:
    ```
    cp package_tree/etc/nginx/sites-available/webilastik.conf /etc/nginx/sites-available/
    ln -s /etc/nginx/sites-available/webilastik.conf /etc/nginx/sites-enabled/webilastik.conf
    ```
- Configure SSL:
    - Add `127.0.0.1 app.ilastik.org` to your `/etc/hosts` file
    - Install a ca cert and create a cert and key, probably via [mkcert](https://github.com/FiloSottile/mkcert):
        - `mkcert -install`
        - `mkcert app.ilastik.org # use the output files from this command in the next step`
    - You can uncomment the following lines in `/etc/nginx/sites-enabled/webilastik.conf` and make them point to your cert and key generated by `mkcert`:
        ```
        #listen 443 ssl;
        #ssl_certificate /etc/webilastik/cert.pem;
        #ssl_certificate_key /etc/webilastik/cert-key.pem;
        ```
- Restart nginx after SSL is configured: `sudo systemctl restart nginx.service`

- Run the "dev" server locally: `task start-local-server`. This task will do some basic checking to see if you have completed the previous steps before attempting to run the server. It will fire the server using `systemctl` to better emulate production behavior, but it will output to the current `tty` so that you don't have to wait for the buffered output while debugging. You can stop the server by running `task stop-local-server`.

## Testing it out:

Once your server is up, just go to https://app.ilastik.org/


# Acknowledgements
This project received funding from the European Union’s Horizon 2020 Framework Programme for Research and Innovation
under the Framework Partnership Agreement No. 650003 (HBP FPA, SGA2 and SGA3).