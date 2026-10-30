### Masters Association

Membership Management app

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app masters_association
```

### Public website

The site's public pages (`/`, `/about`, `/members`, `/gallery`, `/become-members`, …) are a Vue 3 +
[frappe-ui](https://ui.frappe.io) app in `frontend/`, served through `masters_association/www/masters.html`.
Its data comes from the guest APIs in `masters_association/website.py`.

```bash
# production build (bench build runs this too)
cd apps/masters_association/frontend && yarn install && yarn build

# live-reloading dev server, proxied to the bench
cd apps/masters_association/frontend && yarn dev
```

Content is managed from the desk: open **Masters** on `/desk` (or go to `/desk/masters`).

- **Association Member**: approved members with *Show on Website* appear on `/members`. Add rows in
  *Association Positions* for committee roles (committee, position, term); tick *Show in Home Page Team*
  to feature someone on the home page.
- **Gallery Item**: photos and YouTube videos for `/gallery`; *Show on Home Page* adds a photo to the
  home page glimpses.
- **Association Event** and **Association Document**: `/events` and `/documents`.
- **Website Enquiry**: messages from the contact and grievance forms.

### Member portal

Approved Normal/Lifetime members with portal access enabled receive a linked Frappe Website User and
password-setup invitation. They manage their profile at `/member/profile` and verified login-email and
password changes at `/member/account`. Staff use **Masters Manager** for Masters administration;
existing User linkage remains a System Manager action. Existing approved records are invited individually
after migration, without automatic bulk invitations.

See [Member portal and future Solar Monitor](docs/architecture/member-portal-and-solar-monitor.md) for
setup, retry and permission behavior, backend methods, and the future monitoring ownership, global
viewer/manager and anonymous homepage statistics requirements. Solar monitoring and public solar cards
are future work.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/masters_association
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
