# StayDesk demo video: narration script

A first-person story for the capstone demo video (about 8 minutes). Each scene lists what is
on screen and what is said. The video is generated from this file: slides are rendered from
`demo/StayDesk-Final-Presentation.pptx`, the app scenes are a real recording of StayDesk running
in Docker Compose, and the narration is synthesised from the text below.

---

## Scene 1: The problem
**On screen:** title slide

Picture a small hotel on a Friday evening. Two guests walk up to the front desk, both holding a
confirmation for room two-oh-four, for the same night. Somewhere, a spreadsheet said the room
was free twice. That is the kind of mistake I wanted to make impossible.

So I built StayDesk, a front-desk app for hotels. And then, for this capstone, I took it all
the way from my laptop to a monitored, autoscaled Kubernetes cluster on AWS. Let me show you
the app first, and then the journey.

## Scene 2: The dashboard
**On screen:** live app, dashboard

This is the dashboard the front desk opens every morning. At the top: occupancy, today's
arrivals and departures, guests in the house, and the revenue booked this month.

Below that is the worklist for today. Who is arriving, who is due to leave. On the right, every
room in the hotel, coloured by its state: occupied, ready, waiting for housekeeping, or out of
service.

## Scene 3: Taking a booking
**On screen:** live app, new reservation

A guest calls to book. I enter her name and email and choose the dates. Notice the room list.
It only offers rooms that are actually free for those nights, and that are big enough for the
party. The price is worked out as I go: nights, times the nightly rate.

I confirm, and the booking appears straight away. Behind the scenes the API checks for overlaps
again, so even two front-desk staff clicking at the same moment can't double-book a room.

## Scene 4: Check-in and housekeeping
**On screen:** live app, check-in, rooms view

Now an arrival walks in. One click, and the guest is checked in. The room turns occupied on the
dashboard.

When a guest checks out, the room goes to "needs cleaning", and the system won't let anyone
check into a dirty room. Housekeeping marks it clean here, on the rooms page, and it is ready
to sell again. Small rules, but they are exactly the ones a busy desk forgets.

## Scene 5: The journey
**On screen:** slide, the journey

An app that only runs on my laptop is half a project. The real question for this course was:
how does a change travel from my keyboard to real users, safely, and how do we know it is
healthy once it is there?

That journey has thirteen stops. On the top row: the application, git, the CI pipeline, the
Docker image, the security scan and the registry. On the bottom row: Terraform, Kubernetes,
Helm, Ingress, autoscaling, monitoring, and finally troubleshooting.

## Scene 6: At a glance
**On screen:** slide, at a glance

Here are the numbers from the real run. Forty-nine automated tests. Zero fixable high or
critical vulnerabilities. Three minutes and twenty-one seconds from a git push to the new
version running on Amazon EKS. Sixty-one AWS resources created by Terraform, and then
destroyed. The backend scaling itself from two pods to six under load. All of it for about forty
cents of cloud credits.

## Scene 7: Git
**On screen:** slide, git commit

It starts with git. Every change is a small commit with a clear message: a feature, a fix, a
test, the pipeline, the infrastructure. Secrets never go in. Environment files, Terraform state
and variable files are ignored, and I scanned the whole history to be sure.

## Scene 8: The pipeline
**On screen:** slide, CI pipeline

Every push to main wakes up GitHub Actions. First the tests: linting, and those forty-nine
pytest cases, each on its own throwaway database. If a single test fails, nothing after it
runs. Bad code never becomes an image.

Then both images are built and tagged with the commit hash, scanned, pushed, and deployed. One
detail I care about: every third-party action is pinned to an exact commit. In March this
year, attackers hijacked the version tags of a popular security action. A pinned hash can't be
moved.

## Scene 9: Docker
**On screen:** slide, Docker image

The backend and the frontend each get a multi-stage Docker image. Build tools stay in the build
stage. What ships is small: the frontend runtime is twenty-six megabytes, with no Node.js inside.
And neither container runs as root. With one command, docker compose up, the whole stack starts
on any laptop: the database, the API, and the website.

## Scene 10: Security scan
**On screen:** slide, security scan

Before an image is allowed into the registry, Trivy scans it: the operating system packages and
every Python library. The rule is strict. Any high or critical vulnerability that already has a
fix, and the pipeline stops. The result here is zero.

That doesn't mean "secure forever". New vulnerabilities appear every day, which is exactly why
every single build is scanned again.

## Scene 11: The registry
**On screen:** slide, registry

Images that pass go to the GitHub Container Registry. There is no "latest" tag. Each image is
named after the commit it was built from. Commit A becomes image A. So if anything misbehaves
in production, I can point to the exact line of code that is running.

## Scene 12: Terraform
**On screen:** slide, Terraform

Next, the cloud. I didn't click through the AWS console to build anything. Terraform describes
the whole platform as code: a network across two availability zones, public and private
subnets, a NAT gateway, an EKS cluster on Kubernetes one point three five, a worker node, and a
role that lets GitHub deploy without storing a single AWS password.

The plan said sixty-one resources to add, and Terraform built every one of them.

## Scene 13: The AWS Console
**On screen:** slide, AWS Console proof

And here they are, in the real AWS console: the cluster, active and healthy. The network. The
four subnets. The NAT gateway. And the worker node, passing all its health checks.

## Scene 14: Kubernetes
**On screen:** slide, Kubernetes deployment

Now the pipeline can ship to the cluster. GitHub hands the job a short-lived identity token.
AWS checks that it really comes from my repository's main branch, and lets it in. The job runs
helm upgrade, waits for the rollout, and posts a summary.

The result: two backend pods, two frontend pods, and a PostgreSQL database on its own
disk. All running, with zero restarts.

## Scene 15: Helm
**On screen:** slide, Helm

All of that is packaged as one Helm chart. Deployments, services, the database, secrets, the
ingress, the autoscaler, network rules and monitoring, in one versioned package. The same chart
deploys to a local test cluster and to EKS. Only the values change. And if a release goes wrong,
one command rolls it back.

## Scene 16: Ingress
**On screen:** slide, Ingress

How do users reach it? Through one address. Traffic comes in through an AWS load balancer to
Traefik, the ingress controller. Requests for the website go to the frontend. Anything under
slash API goes to the backend.

I chose Traefik on purpose: the old community ingress-nginx project was retired this March, and
I didn't want to build on something that no longer gets security fixes.

## Scene 17: Autoscaling
**On screen:** slide, autoscaling

Then I tried to break it with traffic. Four load generators hammered the API. CPU shot to over
three hundred percent of what each pod had asked for, and within a minute the autoscaler had
gone from two backend pods to six.

But here is the honest part. The sixth pod stayed pending. To save money I was running a single
node, and the autoscaler adds pods, not machines. In production, a cluster autoscaler would add
the node. I'd rather show you that than hide it.

## Scene 18: Monitoring
**On screen:** slide, monitoring

While all that was happening, Prometheus was scraping every pod every fifteen seconds, and
Grafana turned it into this dashboard: requests per second, latency, error rate, and the
autoscaler's replicas climbing in real time. One hundred and sixty-eight requests a second,
ninety-five milliseconds at the ninety-fifth percentile, and zero server errors.

## Scene 19: Troubleshooting
**On screen:** slide, troubleshooting labs

Things will break. So I built three failures I can trigger on purpose. An image tag that doesn't
exist. A service whose label selector matches nothing. And a pod that is running, but never
ready, because it can't reach its database. For each one: the symptom, the command that
reveals it, the root cause, and the fix.

## Scene 20: Real problems
**On screen:** slide, real problems on AWS

And then there were the failures I didn't plan. On a brand-new AWS account, the worker nodes
never appeared: the free plan only allows certain instance types. The load balancer sat at
pending: new accounts can't create the newer kinds yet. And the deploy was rejected because
GitHub had changed the format of its identity tokens. Every one of those was found by reading
the logs, fixed in code, and committed with the reasoning.

## Scene 21: Close
**On screen:** closing slide

So that is StayDesk. A real workflow for a hotel front desk, and a path from a single commit to
a tested, scanned, deployed, autoscaled and monitored application on AWS. Then torn down
cleanly, for about forty cents.

Everything you saw is in the repository, with the evidence for every step. Thank you for
watching.
