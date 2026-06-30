---
title: 'Learning from a multimodal approach with sonoTraining platform'
tags:
  - 
authors:
  - given-names: Natasha
    surname: Bertaina Lucero
    orcid: 0009-0001-2722-4675
    corresponding: true 
    affiliation: "1" # (Multiple affiliations must be quoted)
  - name: Gonzalo Cayo
    equal-contrib: true # (This is how you can denote equal contributions between multiple authors)
    affiliation: 2
  - name: Beatriz García
    orcid: 0000-0003-0919-2734
    equal-contrib: true 
    affiliation: "2"
  - name: Johanna Casado
    orcid: 0000-0001-9528-5034
    equal-contrib: true 
    affiliation: "1"
affiliations:
 - name: Instituto de Bioingeniería, Facultad de Ingeniería, Universidad de Mendoza, Argentina
   index: 1
 - name: Universidad Tecnológica Nacional - Regional Mendoza, Argentina
   index: 2
date: September 9th, 2024
bibliography: paper.bib

---

# Summary

Visual learning styles have dominated the teaching of the natural world, limiting access for those who struggle with these contents. Sonification offers a solution, expanding the possibilities of learning and accessibility in scientific fields. sonoTraining was developed to facilitate the adoption of this technique, it is a web platform that provides accessible training in sonification. Evaluated in a multisensory analysis course in 2024, the platform demonstrated significant improvements in participants, both sighted and blind. These results reinforce the potential of sonoTraining to transform education and research toward a more inclusive and multisensory approach.

# Statement of need

Sonification is a technique that expands the possibilities of learning and accessibility, particularly in scientific fields. Software like sonoUno\footnote{\url{https://www.sonouno.org.ar/}},xSonify\footnote{\url{https://sourceforge.net/projects/xsonify/}}, and StarSound\footnote{\url{https://www.jeffreyhannam.com/starsound/}} have demonstrated the potential of this technology for the deployment, analysis, and interpretation of data, mainly in astronomy, as evidenced by studies such as @wanda2011 and @foran2022. Additionally, recent research by @tucker2022 and @trayford2023 has evaluated the effectiveness of sonification in the analysis of astronomical data, showing that participants in these studies successfully detected variability in astrophysical data, such as changes in star brightness or recognition of chemical elements in galaxy spectra. These results highlight the capacity of sonification to complement standard data analysis in scientific research.


For this technique to be effectively adopted, it is essential to have an adequate teaching and training process. In response to this need, sonoTraining was developed, a web platform specifically designed to host sonification training that does not require expensive installations, an issue highlighted during a previous development with PsychoPy\footnote{\url{https://www.psychopy.org/}} desktop in an International Training Course under the REINFORCE project [bertainaB2023]. The new website facilitates learning the technique, offering an accessible and flexible environment for users of various experience levels to acquire and refine their skills in sonified data analysis. 


# sonoTraining platform

sonoTraining\footnote{\url{Website available: https://sonotraining.um.edu.ar}} is a web platform developed to host and manage data sonification training, based on the Django framework\footnote{\url{https://www.djangoproject.com/}}, a high-level, open-source web development environment. Each data deployment (including sonification and the graph) corresponds to a page of a form, which represents a training block. This organization allows the storage of responses in the database, and form verification ensures that the entire training is completed even in case of interruptions.


To ensure that the forms are readable by assistive technologies, the Web Content Accessibility Guidelines (WCAG\footnote{\url{https://www.w3.org/WAI/standards-guidelines/wcag/es}}) were followed, implementing the recommendations detailed therein. Some functionalities of the Bootstrap framework were also integrated to make the design more fluid, responsive, and without additional loads, helping users with or without assistive technologies to navigate.

# Multimodal training experience

The sonoTraining website was used in its stable version for the first time in a multisensory scientific data analysis course, held between May and June 2024 [@casado2024]. This course was designed to evaluate the tool's capability for non-specialist users, both sighted and blind, with no prior experience in data sonification. The proposed data (taken form open databases) contain mathematical functions, classic astronomical data (related to starlight), and astroparticles (cosmic rays) events These data were mostly represented by 1D graphs on Cartesian axes with a continuous line; in the case of cosmic rays, the representation was with discrete data, representing events, also on Cartesian axes.

The approach to data sonification was new to the course attendees, so support was provided by the-trainers to facilitate the understanding of the data to be analyzed. For the group associated with the visual learning model, graphical representations made with Matplotlib were used. For blind participants, tactile support was provided; for this, a script developed by @farjo2024 was used, which transformed the same graphs used for the sighted group into 3D models with relief.

The training sessions hosted on the sonoTraining web environment consisted of combining the graph and sound or displaying only the sonification. The practices were designed by knowledge block (mathematical functions, light curves, galaxy and star spectra, and cosmic rays), culminating in two practices combining the different types of data.

Eight people participated in this course, divided into two groups with different characteristics. The first group consisted of six members, all sighted, with completed or ongoing university education, and aged between 21 and 53 years. The second group included two blind participants: one with incomplete secondary education and the other with completed tertiary studies. Their ages were 46 and 54. The two groups were formed based on visual capacity to enable a more personalized class. However, the classes for both groups covered the same content through a multisensory deployment. The sonifications used in each training and meeting were the same for both groups.

The course consisted of a weekly in-person session of 2 hours over 8 weeks (16 hours) and homework through the platform (with a variable number of hours, depending on each participant). It was necessary to offer different training to both groups since visually impaired people preferred the WhatsApp platform for their training.

In both cases, simple topics were started, which all participants had previously worked on in their formal education. The first training covered the sonification of mathematical functions, followed by the sonification of the same functions but with added noise. This served as preparation for the following topics: light curves, galaxy spectra, and, finally, particle sonification. The five training sessions were combined to create a review training session, which prepared participants for a final training session with the same structure. During the course, the number of correct answers achieved by each participant was evaluated, with the results shown in \autoref{fig:fig1}.

![Chart of each participant's successes throughout the training sessions \label{fig:fig1}](figures/resultados.png){height="50%"}



# Discussion and Conclusion

The results obtained in the training course with in-person sessions and virtual homework showed evident progress in the correct detection of special features in scientific data through sonification. The pilot course showed significant improvements in both groups, reaching similar levels of accuracy despite differing initial backgrounds. It is worth noting that the group of blind people preferred the use of WhatsApp over sonoTraining because they were not familiar with using web browsers.

The training results reinforce the potential of the training, the use of sonoTraining as a tool, and multisensory analysis as a learning technique, opening new avenues for multimodal and inclusive education and science. sonoTraining promotes the adoption of sonification as a standard tool in research and education, offering inclusive access adapted to different needs.


# References
