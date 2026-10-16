{{/* Chart name, overridable. */}}
{{- define "staydesk.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name. A release called "staydesk" yields "staydesk", so resources are
staydesk-backend, staydesk-frontend, staydesk-postgres.
*/}}
{{- define "staydesk.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "staydesk.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "staydesk.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: staydesk
{{- end }}

{{/* Selector labels for one component; call with (dict "ctx" $ "component" "backend"). */}}
{{- define "staydesk.selectorLabels" -}}
app.kubernetes.io/name: {{ include "staydesk.name" .ctx }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "staydesk.componentLabels" -}}
{{ include "staydesk.labels" .ctx }}
{{ include "staydesk.selectorLabels" . }}
{{- end }}

{{- define "staydesk.backendImage" -}}
{{- printf "%s:%s" .Values.backend.image.repository (.Values.backend.image.tag | default .Chart.AppVersion) }}
{{- end }}

{{- define "staydesk.frontendImage" -}}
{{- printf "%s:%s" .Values.frontend.image.repository (.Values.frontend.image.tag | default .Chart.AppVersion) }}
{{- end }}

{{- define "staydesk.dbSecretName" -}}
{{- printf "%s-db" (include "staydesk.fullname" .) }}
{{- end }}

{{/* Restricted-PSS-compliant container security context. */}}
{{- define "staydesk.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: ["ALL"]
{{- end }}
